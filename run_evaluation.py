#!/usr/bin/env python3
"""Agentic Pattern Evaluation Runner.

Evaluates ReAct, CoT, Reflex, and Tree of Thoughts patterns
Based on evaluation.md specifications.

Phase F (multi-run + statistical rigor): the original single-run flow is
preserved when ``--num-runs 1`` is supplied; otherwise the full
``evaluate_multiple_patterns()`` pipeline is repeated ``--num-runs``
times under identical concurrency / model configuration, results are
flattened into ``PatternRunRecord`` and aggregated through
``aggregate_runs()`` to produce a ``StatisticalReport``.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "agent"))

# Load environment variables BEFORE importing patterns (they call get_llm() at module level)
from dotenv import load_dotenv
load_dotenv()

from pattern_baseline import graph_pattern_baseline
from pattern_react import enhanced_graph_pattern_react, graph_pattern_react
from pattern_reflex import graph_pattern_reflex
from pattern_sequential import graph_pattern_sequential
from pattern_tree_of_thoughts import graph_pattern_tree_of_thoughts

from src.evaluation import (
    ReportGenerator,
    aggregate_runs,
    flatten_pattern_metrics,
    inject_self_consistency_scores,
    load_test_suite,
)
from src.evaluation.evaluator import evaluate_multiple_patterns
from src.evaluation.report_generator import _build_phase_f_metadata
from src.evaluation.visualization import EvaluationVisualizer


def _maybe_inject_self_consistency(
    pattern_metrics,
    per_pattern_runs=None,
    task_outputs=None,
    task_specs=None,
):
    """Phase F hook: refresh Dim1 self-consistency on the latest run.

    No-op when multi-run aggregation is not active (the typical
    single-run path in this script).  Phase F's multi-run loop should
    populate ``per_pattern_runs`` (``{pattern: [run1_results, ...]}``),
    ``task_outputs`` (``{(pattern, task_id): [out1, ...]}``) and
    ``task_specs`` (``{task_id: TestTask}``) and call this helper before
    the report generators run.
    """
    if not per_pattern_runs or not task_outputs or not task_specs:
        return
    inject_self_consistency_scores(
        per_pattern_runs=per_pattern_runs,
        task_outputs=task_outputs,
        task_specs=task_specs,
        pattern_metrics=pattern_metrics,
    )

# ---------------------------------------------------------------------------
# Phase F multi-run orchestrator
# ---------------------------------------------------------------------------

def _reuse_robustness_metrics(target_pattern_metrics, source_pattern_metrics):
    """Copy ``RobustnessMetrics`` from a prior run into a new run's metrics.

    Spec §5.1 cost-control: ``--robustness-once`` reuses the first run's
    perturbation suite to bound wall-clock; the per-run record is then
    populated with that fixed robustness data so all `N` records carry
    identical degradation / stability fields.

    Bug fix (post-2026-05-03 review): we must ALSO propagate the run-1
    ``_normalised_scores.dim6_robustness_scalability`` (Phase E output)
    onto subsequent runs. Without it, ``compute_dim6_scores`` decides
    "no perturbations evidence in this run -> return None", which then
    cascades into:
      - run_records: dim6 = [val, None, None]
      - statistical_summaries: n=1 (CI severely underestimated)
      - single_run_latest = run N -> Dim 6 column collapses to N/A in
        the headline "Dimension Score Summary" table.
    The composite_score also needs to be recomputed from the patched
    NormalizedDimensionScores; we read the old composite recipe by
    importing scoring lazily here to avoid a circular import at module
    load time.
    """
    from src.evaluation.scoring import compute_composite

    for name, target in target_pattern_metrics.items():
        source = source_pattern_metrics.get(name)
        if source is None:
            continue

        # 1) Raw RobustnessMetrics (degradation, stability, scaling, etc.)
        target.robustness = source.robustness

        # 2) Normalised Dim 6 score (the part Phase E lost when no
        #    perturbations were executed this run).
        target_ns = getattr(target, "_normalised_scores", None)
        source_ns = getattr(source, "_normalised_scores", None)
        if target_ns is not None and source_ns is not None:
            target_ns.dim6_robustness_scalability = (
                source_ns.dim6_robustness_scalability
            )
            # Recompute composite so it reflects the patched Dim 6.
            try:
                target._composite_score = compute_composite(target_ns)
            except Exception:
                # Fall back to source composite if recompute fails for
                # any reason -- still better than a stale composite that
                # ignores Dim 6.
                target._composite_score = getattr(source, "_composite_score", None)


async def _run_multi(
    patterns,
    test_tasks,
    *,
    num_runs: int,
    include_robustness: bool,
    delay: float,
    task_timeout: float,
    parallel: bool,
    max_concurrency: int,
    robustness_every_run: bool,
    output_dir: str,
    full_console: bool = False,
):
    """Top-level Phase F multi-run orchestrator.

    Loops ``num_runs`` times, builds the ``PatternRunRecord`` list per
    pattern, calls the Phase B1 self-consistency hook, then writes the
    extended JSON / Markdown / CSV reports and emits the multi-run plots.
    """
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    records_by_pattern: dict = {pattern_name: [] for pattern_name in patterns}
    per_pattern_runs: dict = {pattern_name: [] for pattern_name in patterns}
    task_outputs: dict = {}
    task_specs = {t.id: t for t in test_tasks}

    latest_pattern_metrics = None
    first_run_metrics = None
    robustness_reused = False

    for run_index in range(1, num_runs + 1):
        print(f"\n{'='*60}")
        print(f"  Run {run_index} / {num_runs}")
        print(f"{'='*60}\n")

        # Cost control: only run robustness on the first pass when
        # --robustness-once is selected, then reuse the per-pattern
        # RobustnessMetrics on subsequent passes.
        run_include_robustness = include_robustness and (
            robustness_every_run or run_index == 1
        )

        pattern_metrics = await evaluate_multiple_patterns(
            patterns=patterns,
            test_tasks=test_tasks,
            include_robustness=run_include_robustness,
            delay_between_tasks=delay,
            task_timeout=task_timeout,
            parallel=parallel,
            max_concurrency=max_concurrency,
        )

        if not robustness_every_run and include_robustness:
            if run_index == 1:
                first_run_metrics = pattern_metrics
            else:
                # Replay the first run's robustness data onto this run.
                _reuse_robustness_metrics(pattern_metrics, first_run_metrics)
                robustness_reused = True

        # Phase B1 hook: stash per-task ReasoningQualityResult objects
        # so self-consistency can be computed across runs.
        for pname, pm in pattern_metrics.items():
            cached = getattr(pm, "_per_task_reasoning", None)
            per_pattern_runs[pname].append(cached if cached else [])

        # Capture per-task outputs for self-consistency where available.
        for pname, pm in pattern_metrics.items():
            outputs_per_task = getattr(pm, "_task_outputs_for_run", None)
            if not outputs_per_task:
                continue
            for tid, output in outputs_per_task.items():
                task_outputs.setdefault((pname, tid), []).append(output)

        # Flatten this run into PatternRunRecord per pattern.
        for pname, pm in pattern_metrics.items():
            ns = getattr(pm, "_normalised_scores", None)
            cs = getattr(pm, "_composite_score", None)
            record = flatten_pattern_metrics(
                pattern_metrics=pm,
                normalised_scores=ns,
                composite_score=cs,
                run_index=run_index,
            )
            records_by_pattern[pname].append(record)

        latest_pattern_metrics = pattern_metrics

    # Phase B1 hook: refresh self-consistency on the latest run.  No-op
    # when single-run or when no per-task outputs were captured.
    _maybe_inject_self_consistency(
        latest_pattern_metrics,
        per_pattern_runs=per_pattern_runs,
        task_outputs=task_outputs,
        task_specs=task_specs,
    )

    # Phase F aggregation.
    statistical_report = aggregate_runs(records_by_pattern)

    metadata = _build_phase_f_metadata(
        num_runs=num_runs,
        delay_between_tasks=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
        robustness_reused=robustness_reused,
        insufficient_runs=(num_runs == 1),
    )

    json_path = output_root / "evaluation_results.json"
    md_path = output_root / "evaluation_report.md"
    csv_path = output_root / "comparison_table.csv"

    ReportGenerator.generate_json_report(
        latest_pattern_metrics,
        output_path=str(json_path),
        statistical_report=statistical_report,
        run_metadata=metadata,
    )
    ReportGenerator.generate_markdown_report(
        latest_pattern_metrics,
        output_path=str(md_path),
        statistical_report=statistical_report,
        run_metadata=metadata,
    )
    ReportGenerator.generate_csv_comparison(
        latest_pattern_metrics,
        output_path=str(csv_path),
    )
    if full_console:
        ReportGenerator.print_console_report(latest_pattern_metrics)

    visualizer = EvaluationVisualizer(output_dir=str(output_root / "figures"))
    visualizer.generate_all_plots(
        latest_pattern_metrics,
        statistical_report=statistical_report,
    )

    return latest_pattern_metrics, statistical_report


async def run_full_evaluation(
    delay: float = 1.0,
    task_timeout: float = 180.0,
    parallel: bool = True,
    max_concurrency: int = 2,
    num_runs: int = 1,
    robustness_every_run: bool = True,
    output_dir: str = "reports",
):
    """Run complete evaluation on all patterns (including baseline)."""
    # Define patterns to evaluate -- Baseline (raw LLM) first as control group
    patterns = {
        "Baseline": graph_pattern_baseline,
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        "CoT": graph_pattern_sequential,
        "Reflex": graph_pattern_reflex,
        "ToT": graph_pattern_tree_of_thoughts,
    }

    test_tasks = load_test_suite()

    await _run_multi(
        patterns=patterns,
        test_tasks=test_tasks,
        num_runs=num_runs,
        include_robustness=True,
        delay=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
        robustness_every_run=robustness_every_run,
        output_dir=output_dir,
        full_console=True,
    )


async def run_quick_test(
    delay: float = 1.0,
    task_timeout: float = 180.0,
    parallel: bool = True,
    max_concurrency: int = 2,
    num_runs: int = 1,
    robustness_every_run: bool = True,
    output_dir: str = "reports",
):
    """Run quick test on subset of tasks."""
    patterns = {
        "Baseline": graph_pattern_baseline,
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        # "CoT": graph_pattern_sequential,
    }

    # Use only baseline tasks
    test_tasks = load_test_suite(category="baseline")

    await _run_multi(
        patterns=patterns,
        test_tasks=test_tasks,
        num_runs=num_runs,
        include_robustness=False,
        delay=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
        robustness_every_run=robustness_every_run,
        output_dir=output_dir,
        full_console=True,
    )


async def run_category_test(
    category: str,
    delay: float = 1.0,
    task_timeout: float = 180.0,
    parallel: bool = True,
    max_concurrency: int = 2,
    num_runs: int = 1,
    robustness_every_run: bool = True,
    output_dir: str = "reports",
):
    """Run evaluation on specific category."""
    patterns = {
        "Baseline": graph_pattern_baseline,
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        "CoT": graph_pattern_sequential,
        "Reflex": graph_pattern_reflex,
        "ToT": graph_pattern_tree_of_thoughts,
    }

    test_tasks = load_test_suite(category=category)
    if not test_tasks:
        return

    await _run_multi(
        patterns=patterns,
        test_tasks=test_tasks,
        num_runs=num_runs,
        include_robustness=True,
        delay=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
        robustness_every_run=robustness_every_run,
        output_dir=output_dir,
        full_console=True,
    )


def main():
    """Run the evaluation as main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate agentic design patterns"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "category"],
        default="full",
        help="Evaluation mode (default: full)"
    )
    parser.add_argument(
        "--category",
        choices=["baseline", "reasoning", "tool", "planning"],
        help="Category to evaluate (for category mode)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between tasks to avoid rate limits (default: 1.0)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run patterns sequentially instead of in parallel"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Timeout in seconds per task. Tasks exceeding this are marked as timeout/incomplete (default: 180.0 = 3 minutes)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Max number of patterns to run concurrently in parallel mode (default: 1). "
             "Lower values reduce Ollama resource contention but increase total time."
    )
    # Phase F: multi-run + statistical rigor controls
    parser.add_argument(
        "--num-runs",
        type=int,
        default=3,
        help="Phase F: number of repeated evaluation runs for statistical "
             "rigor (default: 3). Spec valid range: 3-5; values 1-2 are "
             "accepted defensively but mark insufficient_runs=true.",
    )
    robustness_group = parser.add_mutually_exclusive_group()
    robustness_group.add_argument(
        "--robustness-every-run",
        dest="robustness_every_run",
        action="store_true",
        default=True,
        help="Phase F default: re-run the perturbation suite inside every "
             "one of the N runs (honest robustness CI; expensive).",
    )
    robustness_group.add_argument(
        "--robustness-once",
        dest="robustness_every_run",
        action="store_false",
        help="Phase F cost control: run perturbations once on run 1, "
             "reuse for runs 2..N. Sets robustness_reused=true in metadata.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to write reports + figures (default: reports/)",
    )

    args = parser.parse_args()
    parallel = not args.sequential

    if args.num_runs < 1 or args.num_runs > 5:
        print(
            f"WARNING: --num-runs={args.num_runs} is outside the spec range "
            "[1, 5]; clamping to 5."
        )
        args.num_runs = max(1, min(5, args.num_runs))
    if args.num_runs == 1:
        print(
            "WARNING: --num-runs=1 -> confidence intervals collapse to mean; "
            "report metadata will mark insufficient_runs=true."
        )

    start_time = time.time()
    start_dt = datetime.now()
    print(f"\n{'='*60}")
    print(f"  Evaluation started at: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {args.mode} | Delay: {args.delay}s | Timeout: {args.timeout}s | Parallel: {parallel} | Concurrency: {args.concurrency}")
    print(f"  Phase F: num_runs={args.num_runs} | robustness_every_run={args.robustness_every_run}")
    print(f"{'='*60}\n")

    common_kwargs = dict(
        delay=args.delay,
        task_timeout=args.timeout,
        parallel=parallel,
        max_concurrency=args.concurrency,
        num_runs=args.num_runs,
        robustness_every_run=args.robustness_every_run,
        output_dir=args.output_dir,
    )

    if args.mode == "full":
        asyncio.run(run_full_evaluation(**common_kwargs))
    elif args.mode == "quick":
        asyncio.run(run_quick_test(**common_kwargs))
    elif args.mode == "category":
        if not args.category:
            parser.print_help()
            return
        asyncio.run(run_category_test(args.category, **common_kwargs))

    elapsed = time.time() - start_time
    end_dt = datetime.now()
    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\n{'='*60}")
    print(f"  Evaluation finished at: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total elapsed time:     {hours}h {minutes}m {seconds}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
