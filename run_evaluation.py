#!/usr/bin/env python3
"""Agentic Pattern Evaluation Runner.

Evaluates ReAct, CoT, Reflex, and Tree of Thoughts patterns
Based on evaluation.md specifications.
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
    inject_self_consistency_scores,
    load_test_suite,
)
from src.evaluation.evaluator import evaluate_multiple_patterns
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

async def run_full_evaluation(delay: float = 1.0, task_timeout: float = 180.0, parallel: bool = True, max_concurrency: int = 2):
    """Run complete evaluation on all patterns (including baseline)."""
    # Define patterns to evaluate — Baseline (raw LLM) first as control group
    patterns = {
        "Baseline": graph_pattern_baseline,
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        "CoT": graph_pattern_sequential,
        "Reflex": graph_pattern_reflex,
        "ToT": graph_pattern_tree_of_thoughts,
    }

    # Load test suite
    test_tasks = load_test_suite()

    # Run evaluation
    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=True,
        delay_between_tasks=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
    )

    # Generate reports

    # JSON report
    ReportGenerator.generate_json_report(
        pattern_metrics,
        output_path="reports/evaluation_results.json"
    )

    # Markdown report
    ReportGenerator.generate_markdown_report(
        pattern_metrics,
        output_path="reports/evaluation_report.md"
    )

    # CSV comparison
    ReportGenerator.generate_csv_comparison(
        pattern_metrics,
        output_path="reports/comparison_table.csv"
    )

    # Console summary
    ReportGenerator.print_console_report(pattern_metrics)

    # Generate visualizations
    visualizer = EvaluationVisualizer(output_dir="reports/figures")
    visualizer.generate_all_plots(pattern_metrics)



async def run_quick_test(delay: float = 1.0, task_timeout: float = 180.0, parallel: bool = True, max_concurrency: int = 2):
    """Run quick test on subset of tasks."""
    patterns = {
        "Baseline": graph_pattern_baseline,
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        # "CoT": graph_pattern_sequential,
    }

    # Use only baseline tasks
    test_tasks = load_test_suite(category="baseline")

    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=False,
        delay_between_tasks=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
    )

    ReportGenerator.print_console_report(pattern_metrics)


async def run_category_test(category: str, delay: float = 1.0, task_timeout: float = 180.0, parallel: bool = True, max_concurrency: int = 2):
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

    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=True,
        delay_between_tasks=delay,
        task_timeout=task_timeout,
        parallel=parallel,
        max_concurrency=max_concurrency,
    )

    ReportGenerator.print_console_report(pattern_metrics)


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

    args = parser.parse_args()
    parallel = not args.sequential

    start_time = time.time()
    start_dt = datetime.now()
    print(f"\n{'='*60}")
    print(f"  Evaluation started at: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {args.mode} | Delay: {args.delay}s | Timeout: {args.timeout}s | Parallel: {parallel} | Concurrency: {args.concurrency}")
    print(f"{'='*60}\n")

    if args.mode == "full":
        asyncio.run(run_full_evaluation(delay=args.delay, task_timeout=args.timeout, parallel=parallel, max_concurrency=args.concurrency))
    elif args.mode == "quick":
        asyncio.run(run_quick_test(delay=args.delay, task_timeout=args.timeout, parallel=parallel, max_concurrency=args.concurrency))
    elif args.mode == "category":
        if not args.category:
            parser.print_help()
            return
        asyncio.run(run_category_test(args.category, delay=args.delay, task_timeout=args.timeout, parallel=parallel, max_concurrency=args.concurrency))

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
