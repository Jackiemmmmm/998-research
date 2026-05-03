"""Report Generator - Generate evaluation reports."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .metrics import MetricsAggregator, PatternMetrics
from .statistics import StatisticalReport


def _render_statistical_section(
    statistical_report: StatisticalReport,
    run_metadata: Optional[Dict[str, Any]] = None,
) -> list:
    """Render the Phase F "Statistical Rigor" markdown section.

    Produces:

    1. A ``mean ± 95 % CI`` summary table covering the headline metrics.
    2. The pairwise Cohen's d table for ``composite_score``.
    """
    lines = []
    lines.append("## 7. Statistical Rigor (Phase F)")
    lines.append("")
    lines.append(f"Repeated runs: **N = {statistical_report.num_runs}**.")
    if run_metadata is not None and run_metadata.get("robustness_reused"):
        lines.append(
            "> Robustness perturbations were run **once** and replayed; "
            "robustness CI underestimates true variance."
        )
    lines.append("")

    # ------------------------------------------------------------------
    # Mean ± 95% CI summary table
    # ------------------------------------------------------------------
    lines.append("### Mean ± 95 % CI by Pattern")
    lines.append("")
    headline_metrics = [
        ("composite_score", "Composite"),
        ("success_rate_strict", "Success (strict)"),
        ("avg_latency_sec", "Latency (s)"),
        ("avg_total_tokens", "Avg Tokens"),
        ("degradation_percentage", "Degradation %"),
    ]
    header = "| Pattern | " + " | ".join(label for _, label in headline_metrics) + " |"
    sep = "|---------|" + "|".join(["---"] * len(headline_metrics)) + "|"
    lines.append(header)
    lines.append(sep)
    for name, stats in statistical_report.per_pattern.items():
        cells = [name]
        for metric_key, _ in headline_metrics:
            s = stats.summaries.get(metric_key)
            if s is None:
                cells.append("N/A")
            else:
                # Render compactly: mean [low, high]
                cells.append(
                    f"{s.mean:.3f} ± {(s.ci95_high - s.mean):.3f}"
                )
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # ------------------------------------------------------------------
    # Pairwise Cohen's d for composite_score (spec section 5.4 + 5.7)
    # ------------------------------------------------------------------
    lines.append("### Pairwise Effect Sizes — composite_score (Cohen's d)")
    lines.append("")
    lines.append("> Cohen's d magnitudes: 0.2 small, 0.5 medium, 0.8 large.")
    lines.append("> Zero-variance fallback uses ±999.0 to avoid infinities.")
    lines.append("")

    # Caveat (post-2026-05-03 review): when an underlying metric has
    # a very small per-pattern std (e.g. seed_supported=true makes
    # success_rate identical across runs), the pooled std collapses
    # toward 0 and Cohen's d is mathematically correct but practically
    # meaningless -- the standard 0.2/0.5/0.8 thresholds no longer
    # apply.  Emit a heads-up automatically when we detect any pattern
    # whose composite std is below the threshold.
    SMALL_STD_THRESHOLD = 0.01
    composite_stds = []
    for ps in statistical_report.per_pattern.values():
        s = ps.summaries.get("composite_score")
        if s is not None:
            composite_stds.append(s.std)
    if composite_stds and min(composite_stds) < SMALL_STD_THRESHOLD:
        lines.append(
            f"> **Caveat — small-variance inflation**: at least one pattern "
            f"has `std(composite_score) < {SMALL_STD_THRESHOLD}` "
            f"(seed-controlled execution + suppressed robustness variance). "
            f"When pooled std collapses, Cohen's d magnitudes are "
            f"mathematically correct but practically dominated by floating-point "
            f"noise; **do not interpret these via the standard 0.2/0.5/0.8 "
            f"thresholds**. Read these alongside the mean ± CI table above."
        )
        lines.append("")

    composite_pairs = statistical_report.pairwise_effect_sizes.get(
        "composite_score", []
    )
    if not composite_pairs:
        lines.append("_No composite pairwise data available._")
    else:
        lines.append("| Pattern A | Pattern B | Cohen's d |")
        lines.append("|-----------|-----------|-----------|")
        for pair in composite_pairs:
            lines.append(
                f"| {pair.pattern_a} | {pair.pattern_b} | {pair.cohens_d:.3f} |"
            )
    lines.append("")
    return lines


def _git_rev(args: list) -> str:
    """Run ``git rev-parse <args>`` and return stripped stdout, or ``"unknown"``.

    Phase F spec section 5.6: capture branch + commit for reproducibility,
    falling back to ``"unknown"`` on detached-HEAD / missing-binary errors.
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", *args],
            stderr=subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _build_phase_f_metadata(
    num_runs: int,
    delay_between_tasks: Optional[float] = None,
    task_timeout: Optional[float] = None,
    parallel: Optional[bool] = None,
    max_concurrency: Optional[int] = None,
    robustness_reused: bool = False,
    insufficient_runs: bool = False,
) -> Dict[str, Any]:
    """Assemble the Phase F metadata block (spec §5.6 + §5.7).

    Pulls provider/model from ``LLMConfig.get_model_info()``; the judge
    model is resolved from the ``JUDGE_OLLAMA_MODEL`` env var (falls
    back to ``"unknown"`` when unset, matching Phase B1's runtime
    behaviour where it reuses the agent model).
    """
    # Local import to avoid circular dependency at module load time.
    from src.llm_config import LLMConfig

    info = LLMConfig.get_model_info()
    judge_model = os.getenv("JUDGE_OLLAMA_MODEL", "unknown")

    metadata: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "num_runs": num_runs,
        "provider_model": {
            "provider": info.get("provider"),
            "model": info.get("model"),
        },
        "judge_model": judge_model,
        "delay_between_tasks": delay_between_tasks,
        "task_timeout": task_timeout,
        "parallel": parallel,
        "max_concurrency": max_concurrency,
        "robustness_reused": robustness_reused,
        "seed_supported": bool(info.get("seed_supported", False)),
        "seed": info.get("seed"),
        "git_branch": _git_rev(["--abbrev-ref", "HEAD"]),
        "git_commit": _git_rev(["HEAD"]),
    }
    if insufficient_runs:
        metadata["insufficient_runs"] = True
    return metadata


class ReportGenerator:
    """Generate evaluation reports in various formats."""

    @staticmethod
    def generate_json_report(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
        statistical_report: Optional[StatisticalReport] = None,
        run_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate JSON report.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics} for
                the latest single run (back-compat baseline content).
            output_path: Optional path to save report.
            statistical_report: Optional Phase F multi-run aggregate;
                when supplied, ``run_records``, ``statistical_summaries``
                and ``pairwise_effect_sizes`` are added per spec §5.7.
            run_metadata: Optional metadata block (Phase F spec §5.6).
                When supplied it replaces the legacy ``metadata`` block.

        Returns:
            Report dictionary
        """
        # Build comprehensive report
        if run_metadata is not None:
            metadata_block = dict(run_metadata)
            metadata_block.setdefault(
                "patterns_evaluated", list(pattern_metrics.keys())
            )
            metadata_block.setdefault("total_patterns", len(pattern_metrics))
        else:
            metadata_block = {
                "generated_at": datetime.now().isoformat(),
                "patterns_evaluated": list(pattern_metrics.keys()),
                "total_patterns": len(pattern_metrics),
            }

        report = {
            "metadata": metadata_block,
            "individual_metrics": {
                name: metrics.to_dict()
                for name, metrics in pattern_metrics.items()
            },
            "comparison": MetricsAggregator.compare_patterns(pattern_metrics),
        }

        # Phase E: Add normalised scores and composite scores if available
        normalised = {}
        composites = {}
        for name, metrics in pattern_metrics.items():
            ns = getattr(metrics, '_normalised_scores', None)
            cs = getattr(metrics, '_composite_score', None)
            if ns is not None:
                normalised[name] = ns.to_dict()
            if cs is not None:
                composites[name] = cs.to_dict()
        if normalised:
            report["normalised_dimension_scores"] = normalised
        if composites:
            report["composite_scores"] = composites
            # Add ranking
            ranked = sorted(composites.items(), key=lambda x: x[1]["composite"], reverse=True)
            report["composite_ranking"] = [
                {"rank": i + 1, "pattern": name, "composite": data["composite"]}
                for i, (name, data) in enumerate(ranked)
            ]

        # Phase F: Statistical layer (multi-run aggregation).  Schema follows
        # spec §5.7: ``single_run_latest`` mirrors the legacy keying by
        # pattern name; ``run_records``, ``statistical_summaries`` and
        # ``pairwise_effect_sizes`` are added when available.
        if statistical_report is not None:
            report["single_run_latest"] = {
                name: metrics.to_dict()
                for name, metrics in pattern_metrics.items()
            }
            report["run_records"] = {
                name: [r.to_dict() for r in stats.run_records]
                for name, stats in statistical_report.per_pattern.items()
            }
            report["statistical_summaries"] = {
                name: {k: v.to_dict() for k, v in stats.summaries.items()}
                for name, stats in statistical_report.per_pattern.items()
            }
            report["pairwise_effect_sizes"] = {
                metric: [e.to_dict() for e in pairs]
                for metric, pairs in statistical_report.pairwise_effect_sizes.items()
            }

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    @staticmethod
    def generate_markdown_report(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
        statistical_report: Optional[StatisticalReport] = None,
        run_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate Markdown report.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics} for
                the latest single run.
            output_path: Optional path to save report
            statistical_report: Optional Phase F multi-run aggregate;
                when supplied, an additional "Statistical Rigor" section
                is appended with the mean ± 95 % CI summary table and
                pairwise composite-score effect-size table.
            run_metadata: Optional Phase F metadata block.  When
                supplied, the document header surfaces ``num_runs``,
                ``judge_model``, git ref and reproducibility info.

        Returns:
            Markdown string
        """
        comparison = MetricsAggregator.compare_patterns(pattern_metrics)

        # Build markdown
        lines = []
        lines.append("# Agentic Pattern Evaluation Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Patterns Evaluated:** {', '.join(pattern_metrics.keys())}")
        if run_metadata is not None:
            lines.append(f"**Number of Runs:** {run_metadata.get('num_runs', 'unknown')}")
            pm = run_metadata.get("provider_model", {}) or {}
            lines.append(
                f"**Agent Model:** {pm.get('provider', '?')}/{pm.get('model', '?')}"
            )
            lines.append(f"**Judge Model:** {run_metadata.get('judge_model', 'unknown')}")
            lines.append(
                f"**Git:** {run_metadata.get('git_branch', 'unknown')} "
                f"@ {run_metadata.get('git_commit', 'unknown')[:8]}"
            )
            if run_metadata.get("robustness_reused"):
                lines.append(
                    "> **Note:** robustness_reused = true — perturbation suite was "
                    "run **once** and replayed across all runs to bound cost. "
                    "Robustness CI width therefore underestimates true variance."
                )
            if run_metadata.get("insufficient_runs"):
                lines.append(
                    "> **Warning:** num_runs = 1 — confidence intervals are not "
                    "meaningful and the report is marked `insufficient_runs = true`."
                )
        lines.append("")

        num_patterns = len(pattern_metrics)
        lines.append(f"> This report evaluates {num_patterns} agentic design patterns across a 3-layer, 7-dimension")
        lines.append("> framework (Cognitive, Behavioural, Systemic). Each pattern is tested on 16 tasks")
        lines.append("> spanning 4 categories (baseline, reasoning, tool-use, planning) with robustness")
        lines.append("> perturbations. Scores are normalised to [0, 1] for fair cross-pattern comparison.")
        lines.append("")

        # Multi-run helpers used throughout the report (post-2026-05-04 polish):
        # when N>1 we prefer Phase F statistical means over the latest
        # single-run snapshot in headline tables and "Best Pattern" callouts.
        multi_run = (
            statistical_report is not None
            and statistical_report.num_runs > 1
        )

        def _stat_mean(pattern_name: str, metric: str):
            """Return Phase F mean for a metric, or None if absent."""
            if not multi_run:
                return None
            ps = statistical_report.per_pattern.get(pattern_name)
            if ps is None:
                return None
            summary = ps.summaries.get(metric)
            return summary.mean if summary is not None else None

        def _dim_value(pattern_name: str, ns_value, metric: str):
            """Prefer Phase F mean; fall back to single-run normalised score."""
            stat = _stat_mean(pattern_name, metric)
            if stat is not None:
                return stat
            return ns_value

        # Summary table
        lines.append("## Summary Comparison")
        lines.append("")
        lines.append("| Pattern | Strict | Lenient | Gap | Avg Latency (s) | Avg Tokens | Degradation (%) | Controllability |")
        lines.append("|---------|--------|---------|-----|-----------------|------------|-----------------|-----------------|")

        for row in comparison["summary_table"]:
            lines.append(
                f"| {row['pattern']:12s} | "
                f"{row['success_rate_strict']:6.1%} | "
                f"{row['success_rate_lenient']:7.1%} | "
                f"{row['controllability_gap']:3.1%} | "
                f"{row['avg_latency_sec']:15.2f} | "
                f"{row['avg_tokens']:10.0f} | "
                f"{row['degradation_pct']:15.1f} | "
                f"{row['controllability']:15.1%} |"
            )

        lines.append("")

        # Success dimension
        lines.append("## 1. Success Dimension")
        lines.append("")
        lines.append("> **What this measures**: Whether the agent produces correct final answers (strict")
        lines.append("> exact match and lenient extraction). The controllability gap shows how much")
        lines.append("> additional success is recovered by lenient parsing.")
        lines.append("")
        success = comparison["success_dimension"]
        # Post-2026-05-04 review polish: when N>1, use the multi-run
        # statistical mean for the headline rather than the latest
        # single-run snapshot.  Otherwise stochastic patterns like ToT
        # (whose success rate has CI ± 0.155 across 3 runs) get reported
        # at their best run, which overstates capability.
        if multi_run:
            best_pat, best_mean, best_margin = None, -1.0, 0.0
            for pname in pattern_metrics.keys():
                ps = statistical_report.per_pattern.get(pname)
                if ps is None:
                    continue
                s = ps.summaries.get("success_rate_strict")
                if s is None:
                    continue
                if s.mean > best_mean:
                    best_pat, best_mean = pname, s.mean
                    best_margin = s.ci95_high - s.mean
            if best_pat is not None:
                lines.append(
                    f"**Best Pattern (mean across N = {statistical_report.num_runs} runs):** "
                    f"{best_pat} ({best_mean:.1%} strict ± {best_margin:.1%} 95 % CI). "
                    f"_Note: the **latest single run** alone is "
                    f"{success['best_pattern']} ({success['best_score']:.1%}) — different "
                    f"because stochastic patterns (e.g. ToT) vary across runs._"
                )
            else:
                lines.append(f"**Best Pattern:** {success['best_pattern']} ({success['best_score']:.1%})")
        else:
            lines.append(f"**Best Pattern:** {success['best_pattern']} ({success['best_score']:.1%})")
        lines.append("")
        lines.append("### Success Rates by Pattern")
        for pattern, rate in success["rates"].items():
            line = f"- **{pattern}**: {rate:.1%}"
            if multi_run:
                ps = statistical_report.per_pattern.get(pattern)
                if ps is not None:
                    s = ps.summaries.get("success_rate_strict")
                    if s is not None and s.std > 0:
                        line += (
                            f"  _(mean {s.mean:.1%} ± "
                            f"{(s.ci95_high - s.mean):.1%}, n={s.n})_"
                        )
            lines.append(line)
        lines.append("")

        # By category and complexity
        for name, metrics in pattern_metrics.items():
            lines.append(f"#### {name} - By Category")
            for cat, rate in metrics.success.success_by_category.items():
                lines.append(f"  - {cat}: {rate:.1%}")
            lines.append("")

        # Efficiency dimension
        lines.append("## 2. Efficiency Dimension")
        lines.append("")
        lines.append("> **What this measures**: Computational cost of each pattern -- latency (wall-clock")
        lines.append("> time per task) and token consumption. Lower is better. This captures the")
        lines.append("> efficiency vs. capability trade-off central to pattern selection.")
        lines.append("")
        efficiency = comparison["efficiency_dimension"]
        lines.append(f"**Fastest Pattern:** {efficiency['fastest_pattern']} ({efficiency['fastest_latency']:.2f}s)")
        lines.append(f"**Slowest Pattern:** {efficiency['slowest_pattern']} ({efficiency['slowest_latency']:.2f}s)")
        lines.append("")
        lines.append("### Average Latency by Pattern")
        for pattern, latency in efficiency["latencies"].items():
            lines.append(f"- **{pattern}**: {latency:.2f}s")
        lines.append("")

        # Detailed efficiency metrics
        for name, metrics in pattern_metrics.items():
            eff = metrics.efficiency.to_dict()
            lines.append(f"#### {name} - Detailed Efficiency")
            lines.append(f"  - Median Latency: {eff['median_latency_sec']:.2f}s")
            lines.append(f"  - Token Usage: {eff['avg_total_tokens']:.0f} avg")
            lines.append(f"  - Avg Steps: {eff['avg_steps']:.1f}")
            lines.append("")

        # Robustness dimension
        lines.append("## 3. Robustness Dimension")
        lines.append("")
        lines.append("> **What this measures**: How much performance degrades when task prompts are")
        lines.append("> paraphrased or contain typos. Lower degradation = more robust. The D1-enhanced")
        lines.append("> metrics also measure stability across prompt variants and performance scaling")
        lines.append("> from simple to complex tasks.")
        lines.append("")
        robustness = comparison["robustness_dimension"]
        lines.append(f"**Most Robust (raw degradation %):** {robustness['most_robust_pattern']} ({robustness['lowest_degradation']:.1f}% degradation)")
        lines.append(f"**Least Robust (raw degradation %):** {robustness['least_robust_pattern']} ({robustness['highest_degradation']:.1f}% degradation)")
        lines.append("")
        lines.append(
            "> ⚠ **Cross-section note**: this section ranks by *raw* degradation percentage. "
            "The composite **Dim 6** in § 5 combines `norm_degradation × stability_index × scaling_score` "
            "and can give a different ranking — for example, a pattern with the lowest degradation "
            "may still score lower on Dim 6 if its `complexity_decline` is high. **Read both views together.**"
        )
        lines.append("")
        lines.append("### Performance Degradation by Pattern")
        for pattern, deg in robustness["degradations"].items():
            line = f"- **{pattern}**: {deg:.1f}%"
            if multi_run:
                ps = statistical_report.per_pattern.get(pattern)
                if ps is not None:
                    s = ps.summaries.get("degradation_percentage")
                    if s is not None and s.std > 0:
                        line += (
                            f"  _(mean {s.mean:.1f}% ± "
                            f"{(s.ci95_high - s.mean):.1f}%, n={s.n})_"
                        )
            lines.append(line)
        lines.append("")

        # Controllability dimension
        lines.append("## 4. Controllability Dimension")
        lines.append("")
        lines.append("> **What this measures**: Whether the agent operates transparently and within")
        lines.append("> defined constraints -- schema compliance, tool policy adherence, output format")
        lines.append("> consistency, and trace completeness (proportion of complete think-act-observe")
        lines.append("> cycles).")
        lines.append("")
        controllability = comparison["controllability_dimension"]
        lines.append(f"**Most Controllable:** {controllability['most_controllable_pattern']} ({controllability['best_score']:.1%})")
        lines.append("")
        lines.append("### Controllability Scores by Pattern")
        for pattern, score in controllability["scores"].items():
            lines.append(f"- **{pattern}**: {score:.1%}")
        lines.append("")

        # Detailed controllability
        for name, metrics in pattern_metrics.items():
            ctrl = metrics.controllability.to_dict()
            lines.append(f"#### {name} - Detailed Controllability")
            lines.append(f"  - Schema Compliance: {ctrl['schema_compliance_rate']:.1%}")
            lines.append(f"  - Tool Policy Compliance: {ctrl['tool_policy_compliance_rate']:.1%}")
            lines.append(f"  - Format Compliance: {ctrl['format_compliance_rate']:.1%}")
            lines.append(f"  - Unauthorized Tool Uses: {ctrl['unauthorized_tool_uses']}")
            # Phase D2 extended metrics
            cr = getattr(metrics, 'controllability_result', None)
            if cr is not None:
                lines.append(f"  - Trace Completeness: {cr.trace_completeness:.3f}")
                lines.append(f"  - Policy Flag Rate: {cr.policy_flag_rate:.3f}")
                lines.append(f"  - Resource Efficiency: {cr.resource_efficiency:.3f}")
            lines.append("")

        # Alignment dimension (Dim3)
        has_alignment = any(
            m.alignment.total_plan_tasks > 0 for m in pattern_metrics.values()
        )
        if has_alignment:
            lines.append("## 4b. Action-Decision Alignment (Dim 3)")
            lines.append("")
            lines.append("> **What this measures**: Whether agents execute the tools they are supposed to")
            lines.append("> according to the task plan. Coverage measures \"did it call the right tools?\",")
            lines.append("> precision measures \"did it avoid calling wrong tools?\", and sequence match")
            lines.append("> measures \"did it call them in the right order?\".")
            lines.append(">")
            lines.append("> **Note**: Patterns that lack tool-calling capability (e.g. Baseline, Reflex, ToT in")
            lines.append("> this run) are marked N/A -- they cannot be evaluated on this dimension.")
            lines.append("")
            lines.append("| Pattern | Plan Tasks | Aligned | Adherence | Coverage | Precision | Seq Match | Overall |")
            lines.append("|---------|-----------|---------|-----------|----------|-----------|-----------|---------|")
            for name, metrics in pattern_metrics.items():
                am = metrics.alignment
                if am.total_plan_tasks > 0 and am.any_tools_called:
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {am.total_aligned_tasks:7d} | "
                        f"{am.plan_adherence_rate:9.1%} | {am.avg_tool_coverage:8.1%} | "
                        f"{am.avg_tool_precision:9.1%} | {am.avg_sequence_match:9.3f} | "
                        f"{am.overall_alignment():7.3f} |"
                    )
                elif am.total_plan_tasks > 0 and not am.any_tools_called:
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {'N/A':>7s} | "
                        f"{'N/A':>9s} | {'N/A':>8s} | "
                        f"{'N/A':>9s} | {'N/A':>9s} | "
                        f"{'N/A (no tool use)':>7s} |"
                    )
                else:
                    lines.append(f"| {name:12s} | {'N/A':>9s} | {'N/A':>7s} | {'N/A':>9s} | {'N/A':>8s} | {'N/A':>9s} | {'N/A':>9s} | {'N/A':>7s} |")
            lines.append("")

            # Per-task alignment details
            for name, metrics in pattern_metrics.items():
                am = metrics.alignment
                if am.task_alignment_scores:
                    lines.append(f"#### {name} - Per-Task Alignment")
                    for task_id, score in sorted(am.task_alignment_scores.items()):
                        lines.append(f"  - {task_id}: {score:.3f}")
                    lines.append("")

        # Phase E: Normalised Dimension Scores
        has_normalised = any(
            getattr(m, '_normalised_scores', None) is not None
            for m in pattern_metrics.values()
        )
        if has_normalised:
            lines.append("## 5. Normalised Dimension Scores")
            lines.append("")
            lines.append("### Methodology")
            lines.append("")
            lines.append("All sub-indicators are normalised to [0, 1] following the procedure defined in")
            lines.append("the Proposal (§ 2.2): *(1) each sub-indicator is normalised to the 0–1 range;")
            lines.append("(2) dimension-level scores are obtained by averaging the sub-indicators;")
            lines.append("(3) composite results are computed using uniform weighting.*")
            lines.append("")
            lines.append("**Cross-pattern min-max normalisation** is used for latency and token metrics")
            lines.append("(lower is better → inverted): `norm = 1 − (x − x_min) / (x_max − x_min)`.")
            lines.append("When all patterns share the same value or only one pattern has data, the")
            lines.append("normalised score defaults to 1.0.")
            lines.append("")
            lines.append("#### Dim 4 — Success & Efficiency")
            lines.append("")
            lines.append("```")
            lines.append("Dim4 = mean(success_rate, norm_latency, norm_tokens)")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `success_rate` | strict judge pass rate | Already in [0, 1] |")
            lines.append("| `norm_latency` | avg latency (s) | Min-max, inverted (lower = better) |")
            lines.append("| `norm_tokens` | avg total tokens | Min-max, inverted (lower = better) |")
            lines.append("")
            # Build Dim4 detail table
            # Compute norm_latency and norm_tokens inline for the detail table
            from .scoring import normalize_min_max
            all_latencies = [m.efficiency.avg_latency() for m in pattern_metrics.values()]
            all_tokens = [m.efficiency.avg_total_tokens() for m in pattern_metrics.values()]
            lat_opt = [v if v > 0 else None for v in all_latencies]
            tok_opt = [v if v > 0 else None for v in all_tokens]
            norm_lat_list = normalize_min_max(lat_opt, invert=True)
            norm_tok_list = normalize_min_max(tok_opt, invert=True)

            lines.append("**Dim 4 computation detail:**")
            lines.append("")
            lines.append("| Pattern | success_rate | avg_latency (s) | norm_latency | avg_tokens | norm_tokens | Dim 4 |")
            lines.append("|---------|-------------|-----------------|-------------|-----------|------------|-------|")
            for i, (name, m) in enumerate(pattern_metrics.items()):
                sr = m.success.success_rate()
                lat = m.efficiency.avg_latency()
                tok = m.efficiency.avg_total_tokens()
                ns = getattr(m, '_normalised_scores', None)
                d4 = ns.dim4_success_efficiency if ns and ns.dim4_success_efficiency is not None else 0.0
                nl_str = f"{norm_lat_list[i]:.3f}" if norm_lat_list[i] is not None else "N/A"
                nt_str = f"{norm_tok_list[i]:.3f}" if norm_tok_list[i] is not None else "N/A"
                lines.append(
                    f"| {name:12s} | {sr:.3f}       | {lat:15.2f} | {nl_str:>12s} | {tok:9.0f} | {nt_str:>10s} | {d4:.3f} |"
                )
            lines.append("")
            valid_lat = [v for v in all_latencies if v > 0]
            valid_tok = [v for v in all_tokens if v > 0]
            if valid_lat:
                lines.append(f"- Latency range: min = {min(valid_lat):.2f}s, max = {max(valid_lat):.2f}s")
            if valid_tok:
                lines.append(f"- Token range: min = {min(valid_tok):.0f}, max = {max(valid_tok):.0f}")
            lines.append("")

            lines.append("#### Dim 6 — Robustness & Scalability (D1)")
            lines.append("")
            lines.append("```")
            lines.append("Dim6 = mean(norm_degradation, stability_index, scaling_score)")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `norm_degradation` | degradation % | `1 − (degradation / 100)`, clamped to [0, 1] |")
            lines.append("| `stability_index` | prompt-variant consistency | Already in [0, 1] |")
            lines.append("| `scaling_score` | `1 − complexity_decline` | Already in [0, 1] |")
            lines.append("")
            lines.append("**Dim 6 computation detail:**")
            lines.append("")
            lines.append("| Pattern | degradation % | abs_degrad | norm_degrad | stability | scaling | variants | Dim 6 |")
            lines.append("|---------|--------------|-----------|------------|----------|---------|----------|-------|")
            for name, m in pattern_metrics.items():
                rm = m.robustness
                ns = getattr(m, '_normalised_scores', None)
                d6 = ns.dim6_robustness_scalability if ns and ns.dim6_robustness_scalability is not None else None
                nd = max(0.0, min(1.0, 1.0 - rm.degradation_percentage / 100.0))
                d6_str = f"{d6:.3f}" if d6 is not None else "N/A"
                lines.append(
                    f"| {name:12s} | {rm.degradation_percentage:12.1f} | {rm.absolute_degradation:9.3f} | "
                    f"{nd:10.3f} | {rm.stability_index:8.3f} | {rm.scaling_score:7.3f} | "
                    f"{rm.perturbation_variant_count:8d} | {d6_str:>5s} |"
                )
            lines.append("")
            # Success by complexity breakdown
            lines.append("**Success by complexity:**")
            lines.append("")
            for name, m in pattern_metrics.items():
                rm = m.robustness
                if rm.success_by_complexity:
                    parts = ", ".join(f"{k}: {v:.3f}" for k, v in rm.success_by_complexity.items())
                    lines.append(f"- **{name}**: {parts} (decline={rm.complexity_decline:.3f})")
            lines.append("")

            # Auto-generate Dim 6 key finding
            d6_scores = {}
            for name, m in pattern_metrics.items():
                ns = getattr(m, '_normalised_scores', None)
                if ns and ns.dim6_robustness_scalability is not None:
                    d6_scores[name] = ns.dim6_robustness_scalability
            if d6_scores:
                best_robust_name = max(d6_scores, key=d6_scores.get)
                worst_robust_name = min(d6_scores, key=d6_scores.get)
                high_decline = [
                    (n, m.robustness.complexity_decline)
                    for n, m in pattern_metrics.items()
                    if m.robustness.complexity_decline > 0.3
                ]
                lines.append(f"> **Key finding**: {best_robust_name} is the most robust pattern "
                             f"(Dim 6 = {d6_scores[best_robust_name]:.3f}), while {worst_robust_name} "
                             f"is the least robust (Dim 6 = {d6_scores[worst_robust_name]:.3f}).")
                if high_decline:
                    decline_parts = ", ".join(
                        f"{n} ({d:.1%})" for n, d in high_decline
                    )
                    lines.append(f"> Patterns with high complexity decline (>30%): {decline_parts}.")
                lines.append("")

            lines.append("#### Dim 7 — Controllability, Transparency & Resource Efficiency")
            lines.append("")
            lines.append("```")
            lines.append("Dim7 = mean(trace_completeness, 1 − policy_flag_rate, resource_efficiency,")
            lines.append("            schema_compliance, format_compliance)")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `trace_completeness` | (TAO_cycles × 3) / total_steps | Already in [0, 1] |")
            lines.append("| `policy_compliance` | 1 − policy_flag_rate | Already in [0, 1] |")
            lines.append("| `resource_efficiency` | avg tokens, cross-pattern min-max inverted | Min-max, inverted |")
            lines.append("| `schema_compliance` | JSON schema pass rate | Already in [0, 1]; None if no JSON tasks |")
            lines.append("| `format_compliance` | judge pass / successful tasks | Already in [0, 1] |")
            lines.append("")
            lines.append("**Dim 7 computation detail:**")
            lines.append("")
            lines.append("| Pattern | trace_comp | policy_comp | resource_eff | schema_comp | format_comp | Dim 7 |")
            lines.append("|---------|-----------|------------|-------------|------------|------------|-------|")
            for name, m in pattern_metrics.items():
                cm = m.controllability
                cr = getattr(m, 'controllability_result', None)
                ns = getattr(m, '_normalised_scores', None)
                d7 = ns.dim7_controllability if ns and ns.dim7_controllability is not None else 0.0
                tc = f"{cr.trace_completeness:.3f}" if cr else "N/A"
                pc = f"{1.0 - cr.policy_flag_rate:.3f}" if cr else "N/A"
                re = f"{cr.resource_efficiency:.3f}" if cr else "N/A"
                sc = f"{cm.schema_compliance_rate():.3f}" if cm.total_json_tasks > 0 else "N/A"
                fc = f"{cm.format_compliance_rate:.3f}" if cm.format_compliance_rate > 0 else "N/A"
                lines.append(
                    f"| {name:12s} | {tc:>9s} | {pc:>10s} | {re:>11s} | {sc:>10s} | {fc:>10s} | {d7:.3f} |"
                )
            lines.append("")

            lines.append("#### Composite Score")
            lines.append("")
            lines.append("```")
            lines.append("Composite = mean(Dim4, Dim6, Dim7)    [uniform weights, 1/N for N available dimensions]")
            lines.append("```")
            lines.append("")

            lines.append("#### Dim 3 -- Action-Decision Alignment")
            lines.append("")
            lines.append("> **What this measures**: Whether agents execute the tools they are supposed to")
            lines.append("> according to the task plan. Coverage measures \"did it call the right tools?\",")
            lines.append("> precision measures \"did it avoid calling wrong tools?\", and sequence match")
            lines.append("> measures \"did it call them in the right order?\".")
            lines.append(">")
            lines.append("> **Note**: Patterns that lack tool-calling capability are marked N/A -- they")
            lines.append("> cannot be evaluated on this dimension.")
            lines.append("")
            lines.append("```")
            lines.append("Dim3 = mean(plan_adherence_rate, avg_tool_coverage, avg_tool_precision)")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `plan_adherence_rate` | tasks with alignment >= 0.5 / total plan tasks | Already in [0, 1] |")
            lines.append("| `avg_tool_coverage` | mean(|planned ∩ actual| / |planned|) | Already in [0, 1] |")
            lines.append("| `avg_tool_precision` | mean(|planned ∩ actual| / |actual|) | Already in [0, 1] |")
            lines.append("")
            lines.append("**Dim 3 computation detail:**")
            lines.append("")
            lines.append("| Pattern | Plan Tasks | Adherence | Coverage | Precision | Dim 3 |")
            lines.append("|---------|-----------|-----------|----------|-----------|-------|")
            for name, m in pattern_metrics.items():
                am = m.alignment
                ns = getattr(m, '_normalised_scores', None)
                d3 = ns.dim3_action_decision_alignment if ns and ns.dim3_action_decision_alignment is not None else None
                if am.total_plan_tasks > 0 and am.any_tools_called:
                    d3_str = f"{d3:.3f}" if d3 is not None else "N/A"
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {am.plan_adherence_rate:9.3f} | "
                        f"{am.avg_tool_coverage:8.3f} | {am.avg_tool_precision:9.3f} | {d3_str:>5s} |"
                    )
                elif am.total_plan_tasks > 0 and not am.any_tools_called:
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {'N/A':>9s} | "
                        f"{'N/A':>8s} | {'N/A':>9s} | {'N/A (no tool use)':>5s} |"
                    )
                else:
                    lines.append(f"| {name:12s} | {'N/A':>9s} | {'N/A':>9s} | {'N/A':>8s} | {'N/A':>9s} | {'N/A':>5s} |")
            lines.append("")

            lines.append("#### Dim 1 -- Reasoning Quality")
            lines.append("")
            lines.append("> **What this measures**: How coherent and well-grounded the agent's")
            lines.append("> reasoning trace is. Combines four sub-indicators: trace_coverage (does the")
            lines.append("> agent show its work?), coherence (does the chain hold together, judged by a")
            lines.append("> separate local LLM), final-answer agreement (does the conclusion match the")
            lines.append("> reasoning?), and self-consistency (do repeated runs converge on the same")
            lines.append("> answer; only filled in when --num-runs > 1).")
            lines.append(">")
            lines.append("> **Note**: Patterns with zero usable THINK steps (e.g. Baseline) are still")
            lines.append("> evaluable but score 0 on coverage and coherence; their Dim1 is dominated by")
            lines.append("> the renormalised final-answer agreement.")
            lines.append("")
            lines.append("```")
            lines.append("Dim1 = 0.15*coverage + 0.40*coherence + 0.20*answer_agreement + 0.25*self_consistency")
            lines.append("Dim1 = renorm(coverage, coherence, answer_agreement)   [single-run]")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `trace_coverage` | min(1, think_steps / 2) | Already in [0, 1] |")
            lines.append("| `coherence_score` | judge LLM mean(logical_progression, internal_consistency) | Already in [0, 1] |")
            lines.append("| `final_answer_agreement` | strict=1.0 / lenient=0.5 / fail=0.0 | Already in [0, 1] |")
            lines.append("| `self_consistency_score` | largest equivalence class / total runs | Already in [0, 1]; None when single-run |")
            lines.append("")
            lines.append("**Dim 1 computation detail:**")
            lines.append("")
            lines.append("| Pattern | Tasks w/ Reason. | Coverage | Coherence | Agreement | Self-Cons. | Fallbacks | Dim 1 |")
            lines.append("|---------|------------------|----------|-----------|-----------|------------|-----------|-------|")
            for name, metrics in pattern_metrics.items():
                cog = metrics.cognitive
                ns = getattr(metrics, '_normalised_scores', None)
                d1 = ns.dim1_reasoning_quality if ns and ns.dim1_reasoning_quality is not None else None
                d1_str = f"{d1:.3f}" if d1 is not None else "N/A"
                sc_str = (
                    f"{cog.avg_self_consistency_score:.3f}"
                    if cog.avg_self_consistency_score is not None
                    else "N/A"
                )
                lines.append(
                    f"| {name:12s} | {cog.tasks_with_reasoning:16d} | "
                    f"{cog.avg_trace_coverage:8.3f} | {cog.avg_coherence_score:9.3f} | "
                    f"{cog.avg_final_answer_agreement:9.3f} | {sc_str:>10s} | "
                    f"{cog.judge_fallback_count:9d} | {d1_str:>5s} |"
                )
            lines.append("")

            lines.append("#### Dim 5 -- Behavioural Safety")
            lines.append("")
            lines.append("> **What this measures**: Whether agents respect safety boundaries -- tool whitelist")
            lines.append("> compliance (only calling authorised tools) and content safety (no dangerous")
            lines.append("> patterns like shell commands, SQL injection, or PII exposure in outputs).")
            lines.append(">")
            lines.append("> **Note**: Patterns with zero tool calls have tool compliance marked as N/A")
            lines.append("> (not evaluable). Their Dim5 score is based on domain safety only.")
            lines.append("")
            lines.append("```")
            lines.append("Dim5 = mean(tool_compliance_rate, domain_safety_score)  [when tool calls > 0]")
            lines.append("Dim5 = domain_safety_score                              [when tool calls == 0]")
            lines.append("```")
            lines.append("")
            lines.append("| Sub-indicator | Source | Normalisation |")
            lines.append("|---------------|--------|---------------|")
            lines.append("| `tool_compliance_rate` | 1 - (unauthorized / total tool calls) | Already in [0, 1] |")
            lines.append("| `domain_safety_score` | 1 - (flagged tasks / scanned tasks) | Already in [0, 1] |")
            lines.append("")
            lines.append("**Dim 5 computation detail:**")
            lines.append("")
            lines.append("| Pattern | Tool Tasks | Tool Calls | Violations | Compliance | Flagged | Scanned | Domain Safety | Dim 5 |")
            lines.append("|---------|-----------|-----------|-----------|-----------|---------|---------|--------------|-------|")
            for name, metrics in pattern_metrics.items():
                sm = metrics.safety
                ns = getattr(metrics, '_normalised_scores', None)
                d5 = ns.dim5_behavioural_safety if ns and ns.dim5_behavioural_safety is not None else None
                d5_str = f"{d5:.3f}" if d5 is not None else "N/A"
                compliance_str = (
                    f"{sm.tool_compliance_rate:9.3f}"
                    if sm.total_tool_calls > 0
                    else "N/A (no calls)"
                )
                lines.append(
                    f"| {name:12s} | {sm.total_tool_tasks:9d} | {sm.total_tool_calls:9d} | "
                    f"{sm.unauthorized_tool_calls:9d} | {compliance_str:>9s} | "
                    f"{sm.tasks_flagged_unsafe:7d} | {sm.total_tasks_scanned:7d} | "
                    f"{sm.domain_safety_score:12.3f} | {d5_str:>5s} |"
                )
            lines.append("")

            # Dim 2 placeholder note (post-2026-05-04 polish): Phase B2
            # is owned by P3 and not yet implemented; we surface this
            # explicitly so readers don't think Dim 2 is silently zero.
            lines.append("#### Dim 2 -- Cognitive Safety & Constraint Adherence")
            lines.append("")
            lines.append(
                "> 🚧 **Not yet implemented** — Phase B2 is owned by **P3 (Kapila)** per the "
                "[10-week project plan](./10_WEEK_PROJECT_PLAN_EN.md#week-56-cognitive-layer--statistical-rigor) "
                "Week 5-6 row. The forward-compatibility field `dim2_cognitive_safety` already exists in "
                "`run_records` and `PatternRunRecord`; it will populate automatically once Phase B2 "
                "lands without any further Phase F changes."
            )
            lines.append("")
            lines.append(
                "Planned scope (per [Group-1.pdf § 2.2.1 Dim2](../Group-1.pdf)): "
                "toxicity keyword filtering, unsupported-claim / hallucination detection, "
                "and constraint-adherence scoring."
            )
            lines.append("")

            # Phase F bug fix: when statistical_report is available
            # (multi-run), prefer the per-pattern statistical mean over
            # the latest single-run snapshot for each dimension.
            # `multi_run`, `_stat_mean`, `_dim_value` are defined at
            # the top of generate_markdown_report (lifted post-2026-05-04
            # polish so they can be reused in section 1 and elsewhere).
            lines.append("### Dimension Score Summary")
            lines.append("")
            if multi_run:
                lines.append(
                    f"> Values are mean across **N = {statistical_report.num_runs} runs** "
                    f"(Phase F `statistical_summaries`). Patterns/dimensions with `N/A` "
                    f"have all-`None` runs (e.g. Baseline has no THINK steps -> Dim 1 N/A)."
                )
                lines.append("")
            lines.append("| Pattern | Dim 1 (Reason) | Dim 3 (Align) | Dim 4 (Success) | Dim 5 (Safety) | Dim 6 (Robust) | Dim 7 (Control) | Composite |")
            lines.append("|---------|----------------|--------------|----------------|----------------|----------------|-----------------|-----------|")
            for name, metrics in pattern_metrics.items():
                ns = getattr(metrics, '_normalised_scores', None)
                cs = getattr(metrics, '_composite_score', None)
                d1_v = _dim_value(name, ns.dim1_reasoning_quality if ns else None, "dim1_reasoning_quality")
                d3_v = _dim_value(name, ns.dim3_action_decision_alignment if ns else None, "dim3_action_decision_alignment")
                d4_v = _dim_value(name, ns.dim4_success_efficiency if ns else None, "dim4_success_efficiency")
                d5_v = _dim_value(name, ns.dim5_behavioural_safety if ns else None, "dim5_behavioural_safety")
                d6_v = _dim_value(name, ns.dim6_robustness_scalability if ns else None, "dim6_robustness_scalability")
                d7_v = _dim_value(name, ns.dim7_controllability if ns else None, "dim7_controllability")
                comp_v = _dim_value(name, cs.composite if cs else None, "composite_score")
                d1 = f"{d1_v:.3f}" if d1_v is not None else "N/A"
                d3 = f"{d3_v:.3f}" if d3_v is not None else "N/A"
                d4 = f"{d4_v:.3f}" if d4_v is not None else "N/A"
                d5 = f"{d5_v:.3f}" if d5_v is not None else "N/A"
                d6 = f"{d6_v:.3f}" if d6_v is not None else "N/A"
                d7 = f"{d7_v:.3f}" if d7_v is not None else "N/A"
                comp = f"{comp_v:.3f}" if comp_v is not None else "N/A"
                lines.append(f"| {name:12s} | {d1:14s} | {d3:12s} | {d4:14s} | {d5:14s} | {d6:14s} | {d7:15s} | {comp:9s} |")
            lines.append("")

            # Reserve indicators
            lines.append("### Reserve Indicators (★)")
            lines.append("")
            lines.append("| Pattern | Norm Steps | Norm Tool Calls | Norm TAO Cycles |")
            lines.append("|---------|-----------|-----------------|-----------------|")
            for name, metrics in pattern_metrics.items():
                ns = getattr(metrics, '_normalised_scores', None)
                if ns:
                    s = f"{ns.norm_avg_steps:.3f}" if ns.norm_avg_steps is not None else "N/A"
                    tc = f"{ns.norm_avg_tool_calls:.3f}" if ns.norm_avg_tool_calls is not None else "N/A"
                    tao = f"{ns.norm_tao_cycles:.3f}" if ns.norm_tao_cycles is not None else "N/A"
                    lines.append(f"| {name:12s} | {s:9s} | {tc:15s} | {tao:15s} |")
            lines.append("")

            # Composite ranking — dual view per post-2026-05-03 review:
            # the "evaluable-dim mean" view is honest to the spec but
            # rewards patterns with more N/A dimensions (e.g. Baseline,
            # which is a raw-LLM control with no reasoning trace and no
            # tool use, gets averaged over only 3 dimensions and ends up
            # ranking #1).  We additionally surface an "all-7-dim mean
            # (N/A=0)" view so the supervisor can compare both.
            composites = []
            for name, metrics in pattern_metrics.items():
                cs = getattr(metrics, '_composite_score', None)
                ns = getattr(metrics, '_normalised_scores', None)
                if cs is None or ns is None:
                    continue
                # Collect all 7 normalised dim scores
                seven_dims = [
                    ns.dim1_reasoning_quality,
                    ns.dim2_cognitive_safety,
                    ns.dim3_action_decision_alignment,
                    ns.dim4_success_efficiency,
                    ns.dim5_behavioural_safety,
                    ns.dim6_robustness_scalability,
                    ns.dim7_controllability,
                ]
                # Override with Phase F means where available (multi-run).
                if multi_run:
                    metric_names = [
                        "dim1_reasoning_quality",
                        "dim2_cognitive_safety",
                        "dim3_action_decision_alignment",
                        "dim4_success_efficiency",
                        "dim5_behavioural_safety",
                        "dim6_robustness_scalability",
                        "dim7_controllability",
                    ]
                    for i, m in enumerate(metric_names):
                        stat = _stat_mean(name, m)
                        if stat is not None:
                            seven_dims[i] = stat
                # All-7-dim mean treats N/A as 0.
                penalised = sum((v if v is not None else 0.0) for v in seven_dims) / 7.0
                composites.append((name, cs.composite, cs.available_dimensions, penalised))
            if composites:
                # Default ranking: by evaluable-dim mean (current spec behaviour)
                composites.sort(key=lambda x: x[1], reverse=True)
                lines.append("### Composite Score Ranking")
                lines.append("")
                lines.append("> **Read this caveat first**: two composite views are reported below because")
                lines.append("> the spec's \"evaluable-dim mean\" rewards patterns with more N/A dimensions.")
                lines.append("> For example, **Baseline (raw-LLM control)** has N/A on Dim 1 (no reasoning trace)")
                lines.append("> and Dim 3 (no tool use), so its composite averages over only 3 dimensions while")
                lines.append("> tool/reasoning patterns like CoT average over 5. **Always read these rankings")
                lines.append("> alongside the per-dimension breakdown above** — a single number cannot capture")
                lines.append("> patterns that are unmeasurable on a dimension vs. patterns that fail it.")
                lines.append("")
                lines.append("**View A — Evaluable-dim mean** (spec §5.7, uniform weight over available dims):")
                lines.append("")
                for rank, (name, score, n_dims, _) in enumerate(composites, 1):
                    lines.append(f"{rank}. **{name}**: {score:.4f} ({n_dims} dimensions)")
                lines.append("")
                # Penalised view (N/A=0)
                penalised_sorted = sorted(composites, key=lambda x: x[3], reverse=True)
                lines.append("**View B — All-7-dim mean (N/A treated as 0)**: penalises unmeasurable dimensions.")
                lines.append("Useful for comparing patterns on equal footing, but harsh on the raw-LLM control.")
                lines.append("")
                for rank, (name, _spec_score, _n_dims, penalised) in enumerate(penalised_sorted, 1):
                    lines.append(f"{rank}. **{name}**: {penalised:.4f}")
                lines.append("")

        # Recommendations
        lines.append("## 6. Recommendations")
        lines.append("")
        lines.append("### Scenario-Based Pattern Selection")
        lines.append("")

        # Find best for each scenario.
        # "Complex Reasoning Tasks" must use Dim 1 (reasoning quality)
        # NOT raw success rate -- otherwise the raw-LLM Baseline (which
        # has no reasoning trace at all and is N/A on Dim 1) would be
        # falsely recommended for tasks that explicitly need reasoning.
        # See post-2026-05-03 review.
        def _dim1_score(item):
            ns = getattr(item[1], '_normalised_scores', None)
            if ns and ns.dim1_reasoning_quality is not None:
                return ns.dim1_reasoning_quality
            return -1.0  # patterns without reasoning are not eligible

        best_reasoning_candidates = [
            (k, v) for k, v in pattern_metrics.items() if _dim1_score((k, v)) >= 0
        ]
        if best_reasoning_candidates:
            best_reasoning = max(best_reasoning_candidates, key=_dim1_score)
            best_reasoning_score = _dim1_score(best_reasoning)
            best_reasoning_label = (
                f"{best_reasoning[0]} (Dim 1 reasoning quality = "
                f"{best_reasoning_score:.3f})"
            )
        else:
            best_reasoning_label = "no pattern produced an evaluable reasoning trace"

        best_success = max(pattern_metrics.items(), key=lambda x: x[1].success.success_rate())
        best_speed = min(
            ((k, v) for k, v in pattern_metrics.items() if v.efficiency.avg_latency() > 0),
            key=lambda x: x[1].efficiency.avg_latency(),
            default=best_success,
        )
        best_robust = min(pattern_metrics.items(), key=lambda x: x[1].robustness.degradation_percentage)
        # Use Dim 7 normalised score if available, fall back to overall_controllability
        def _dim7_score(item):
            ns = getattr(item[1], '_normalised_scores', None)
            if ns and ns.dim7_controllability is not None:
                return ns.dim7_controllability
            return item[1].controllability.overall_controllability()
        best_control = max(pattern_metrics.items(), key=_dim7_score)

        lines.append(
            f"- **Complex Reasoning Tasks:** {best_reasoning_label} -- highest *evaluable* "
            f"reasoning quality. Patterns with N/A on Dim 1 (e.g. Baseline) are excluded."
        )
        lines.append(
            f"- **Highest Raw Success Rate (any task type):** {best_success[0]} "
            f"({best_success[1].success.success_rate()*100:.1f}%) -- note this includes "
            f"patterns that succeed without reasoning."
        )
        lines.append(f"- **Real-time/Low-latency Scenarios:** {best_speed[0]} (fastest response)")
        lines.append(f"- **Noisy/Unreliable Environments:** {best_robust[0]} (most robust)")
        lines.append(f"- **Enterprise/Compliance-critical:** {best_control[0]} (most controllable)")
        lines.append("")

        # Key trade-offs analysis (auto-generated)
        lines.append("### Key Trade-offs Observed")
        lines.append("")

        # Tool-using vs non-tool patterns trade-off
        tool_patterns = []
        non_tool_patterns = []
        for name, m in pattern_metrics.items():
            if m.alignment.any_tools_called:
                tool_patterns.append(name)
            else:
                non_tool_patterns.append(name)
        if tool_patterns and non_tool_patterns:
            tool_success = sum(
                pattern_metrics[n].success.success_rate() for n in tool_patterns
            ) / len(tool_patterns)
            non_tool_success = sum(
                pattern_metrics[n].success.success_rate() for n in non_tool_patterns
            ) / len(non_tool_patterns)
            lines.append(
                f"- **Tool-using patterns ({', '.join(tool_patterns)}) vs "
                f"Non-tool patterns ({', '.join(non_tool_patterns)})**: "
                f"Tool-using patterns average {tool_success:.1%} success vs "
                f"{non_tool_success:.1%} for non-tool patterns. "
                f"Tool-using patterns can be evaluated on Dim 3 (alignment), "
                f"while non-tool patterns receive N/A for that dimension."
            )

        # Efficiency vs Capability trade-off
        if best_success[0] != best_speed[0]:
            lines.append(
                f"- **Efficiency vs Capability**: "
                f"{best_speed[0]} is the fastest ({best_speed[1].efficiency.avg_latency():.2f}s avg) "
                f"but {best_success[0]} achieves the highest success rate "
                f"({best_success[1].success.success_rate():.1%}). "
                f"Selecting a pattern requires balancing response time against accuracy."
            )

        # Robustness vs Complexity handling trade-off
        high_stability = [(n, m.robustness.stability_index) for n, m in pattern_metrics.items()
                          if m.robustness.stability_index > 0]
        high_decline_patterns = [(n, m.robustness.complexity_decline) for n, m in pattern_metrics.items()
                                 if m.robustness.complexity_decline > 0.2]
        if high_stability:
            best_stability_name = max(high_stability, key=lambda x: x[1])
            lines.append(
                f"- **Robustness vs Complexity handling**: "
                f"{best_stability_name[0]} shows the highest prompt stability "
                f"(index={best_stability_name[1]:.3f})."
            )
            if high_decline_patterns:
                decline_parts = ", ".join(f"{n} ({d:.1%})" for n, d in high_decline_patterns)
                lines.append(
                    f"  However, patterns with notable complexity decline: {decline_parts}."
                )
        lines.append("")

        # Phase F: Statistical Rigor section.  Renders the mean ± 95 % CI
        # summary table for headline metrics + the pairwise composite
        # effect-size table (spec §5.7).
        if statistical_report is not None:
            lines.extend(
                _render_statistical_section(statistical_report, run_metadata)
            )

        markdown = "\n".join(lines)

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

        return markdown

    @staticmethod
    def generate_csv_comparison(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
    ) -> str:
        """Generate CSV comparison table.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}
            output_path: Optional path to save CSV

        Returns:
            CSV string
        """
        comparison = MetricsAggregator.compare_patterns(pattern_metrics)

        # Build CSV
        lines = []
        header = "Pattern,Success Rate (Strict),Success Rate (Lenient),Controllability Gap,Avg Latency (s),Avg Tokens,Degradation (%),Controllability,Alignment"
        # D1 columns
        header += ",Abs Degradation,Perturbation Variants,Stability Index,Complexity Decline,Scaling Score"
        # D2 + E columns
        header += ",Trace Completeness,Policy Flag Rate,Resource Efficiency"
        # B1: Dim1 reasoning quality sub-indicators
        header += ",Reasoning Tasks With Trace,Avg Trace Coverage,Avg Coherence,Avg Answer Agreement,Avg Self-Consistency,Judge Fallback Count"
        header += ",Dim1,Dim3,Dim4,Dim5,Dim6,Dim7,Composite"
        lines.append(header)

        for row in comparison["summary_table"]:
            pname = row['pattern']
            metrics = pattern_metrics.get(pname)
            line = (
                f"{pname},"
                f"{row['success_rate_strict']:.3f},"
                f"{row['success_rate_lenient']:.3f},"
                f"{row['controllability_gap']:.3f},"
                f"{row['avg_latency_sec']:.2f},"
                f"{row['avg_tokens']:.0f},"
                f"{row['degradation_pct']:.2f},"
                f"{row['controllability']:.3f},"
                f"{row['alignment']:.3f}"
            )
            # D1 sub-indicators
            if metrics:
                rm = metrics.robustness
                line += (
                    f",{rm.absolute_degradation:.4f}"
                    f",{rm.perturbation_variant_count}"
                    f",{rm.stability_index:.4f}"
                    f",{rm.complexity_decline:.4f}"
                    f",{rm.scaling_score:.4f}"
                )
            else:
                line += ",,,,,"
            # D2 sub-indicators
            cr = getattr(metrics, 'controllability_result', None) if metrics else None
            if cr:
                line += f",{cr.trace_completeness:.4f},{cr.policy_flag_rate:.4f},{cr.resource_efficiency:.4f}"
            else:
                line += ",,,"
            # B1: Dim1 reasoning quality sub-indicators
            if metrics:
                cog = metrics.cognitive
                sc_str = (
                    f"{cog.avg_self_consistency_score:.4f}"
                    if cog.avg_self_consistency_score is not None
                    else ""
                )
                line += (
                    f",{cog.tasks_with_reasoning}"
                    f",{cog.avg_trace_coverage:.4f}"
                    f",{cog.avg_coherence_score:.4f}"
                    f",{cog.avg_final_answer_agreement:.4f}"
                    f",{sc_str}"
                    f",{cog.judge_fallback_count}"
                )
            else:
                line += ",,,,,,"
            # E normalised scores
            ns = getattr(metrics, '_normalised_scores', None) if metrics else None
            cs = getattr(metrics, '_composite_score', None) if metrics else None
            d1 = f"{ns.dim1_reasoning_quality:.4f}" if ns and ns.dim1_reasoning_quality is not None else ""
            d3 = f"{ns.dim3_action_decision_alignment:.4f}" if ns and ns.dim3_action_decision_alignment is not None else ""
            d4 = f"{ns.dim4_success_efficiency:.4f}" if ns and ns.dim4_success_efficiency is not None else ""
            d5 = f"{ns.dim5_behavioural_safety:.4f}" if ns and ns.dim5_behavioural_safety is not None else ""
            d6 = f"{ns.dim6_robustness_scalability:.4f}" if ns and ns.dim6_robustness_scalability is not None else ""
            d7 = f"{ns.dim7_controllability:.4f}" if ns and ns.dim7_controllability is not None else ""
            comp = f"{cs.composite:.4f}" if cs else ""
            line += f",{d1},{d3},{d4},{d5},{d6},{d7},{comp}"
            lines.append(line)

        csv = "\n".join(lines)

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(csv)

        return csv

    @staticmethod
    def print_console_report(pattern_metrics: Dict[str, PatternMetrics]):
        """Print a concise report to console."""
        comparison = MetricsAggregator.compare_patterns(pattern_metrics)


        # Summary table with both success rates

        for row in comparison["summary_table"]:
            pass


        # Winners

