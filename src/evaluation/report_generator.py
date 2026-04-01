"""Report Generator - Generate evaluation reports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .metrics import MetricsAggregator, PatternMetrics


class ReportGenerator:
    """Generate evaluation reports in various formats."""

    @staticmethod
    def generate_json_report(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate JSON report.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}
            output_path: Optional path to save report

        Returns:
            Report dictionary
        """
        # Build comprehensive report
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "patterns_evaluated": list(pattern_metrics.keys()),
                "total_patterns": len(pattern_metrics),
            },
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
    ) -> str:
        """Generate Markdown report.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}
            output_path: Optional path to save report

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
        lines.append("")

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
        success = comparison["success_dimension"]
        lines.append(f"**Best Pattern:** {success['best_pattern']} ({success['best_score']:.1%})")
        lines.append("")
        lines.append("### Success Rates by Pattern")
        for pattern, rate in success["rates"].items():
            lines.append(f"- **{pattern}**: {rate:.1%}")
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
        robustness = comparison["robustness_dimension"]
        lines.append(f"**Most Robust:** {robustness['most_robust_pattern']} ({robustness['lowest_degradation']:.1f}% degradation)")
        lines.append(f"**Least Robust:** {robustness['least_robust_pattern']} ({robustness['highest_degradation']:.1f}% degradation)")
        lines.append("")
        lines.append("### Performance Degradation by Pattern")
        for pattern, deg in robustness["degradations"].items():
            lines.append(f"- **{pattern}**: {deg:.1f}%")
        lines.append("")

        # Controllability dimension
        lines.append("## 4. Controllability Dimension")
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
            lines.append("| Pattern | Plan Tasks | Aligned | Adherence | Coverage | Precision | Seq Match | Overall |")
            lines.append("|---------|-----------|---------|-----------|----------|-----------|-----------|---------|")
            for name, metrics in pattern_metrics.items():
                am = metrics.alignment
                if am.total_plan_tasks > 0:
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {am.total_aligned_tasks:7d} | "
                        f"{am.plan_adherence_rate:9.1%} | {am.avg_tool_coverage:8.1%} | "
                        f"{am.avg_tool_precision:9.1%} | {am.avg_sequence_match:9.3f} | "
                        f"{am.overall_alignment():7.3f} |"
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
                if am.total_plan_tasks > 0:
                    d3_str = f"{d3:.3f}" if d3 is not None else "N/A"
                    lines.append(
                        f"| {name:12s} | {am.total_plan_tasks:9d} | {am.plan_adherence_rate:9.3f} | "
                        f"{am.avg_tool_coverage:8.3f} | {am.avg_tool_precision:9.3f} | {d3_str:>5s} |"
                    )
                else:
                    lines.append(f"| {name:12s} | {'N/A':>9s} | {'N/A':>9s} | {'N/A':>8s} | {'N/A':>9s} | {'N/A':>5s} |")
            lines.append("")

            lines.append("#### Dim 5 -- Behavioural Safety")
            lines.append("")
            lines.append("```")
            lines.append("Dim5 = mean(tool_compliance_rate, domain_safety_score)")
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
                lines.append(
                    f"| {name:12s} | {sm.total_tool_tasks:9d} | {sm.total_tool_calls:9d} | "
                    f"{sm.unauthorized_tool_calls:9d} | {sm.tool_compliance_rate:9.3f} | "
                    f"{sm.tasks_flagged_unsafe:7d} | {sm.total_tasks_scanned:7d} | "
                    f"{sm.domain_safety_score:12.3f} | {d5_str:>5s} |"
                )
            lines.append("")

            lines.append("### Dimension Score Summary")
            lines.append("")
            lines.append("| Pattern | Dim 3 (Align) | Dim 4 (Success) | Dim 5 (Safety) | Dim 6 (Robust) | Dim 7 (Control) | Composite |")
            lines.append("|---------|--------------|----------------|----------------|----------------|-----------------|-----------|")
            for name, metrics in pattern_metrics.items():
                ns = getattr(metrics, '_normalised_scores', None)
                cs = getattr(metrics, '_composite_score', None)
                d3 = f"{ns.dim3_action_decision_alignment:.3f}" if ns and ns.dim3_action_decision_alignment is not None else "N/A"
                d4 = f"{ns.dim4_success_efficiency:.3f}" if ns and ns.dim4_success_efficiency is not None else "N/A"
                d5 = f"{ns.dim5_behavioural_safety:.3f}" if ns and ns.dim5_behavioural_safety is not None else "N/A"
                d6 = f"{ns.dim6_robustness_scalability:.3f}" if ns and ns.dim6_robustness_scalability is not None else "N/A"
                d7 = f"{ns.dim7_controllability:.3f}" if ns and ns.dim7_controllability is not None else "N/A"
                comp = f"{cs.composite:.3f}" if cs else "N/A"
                lines.append(f"| {name:12s} | {d3:12s} | {d4:14s} | {d5:14s} | {d6:14s} | {d7:15s} | {comp:9s} |")
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

            # Composite ranking
            composites = []
            for name, metrics in pattern_metrics.items():
                cs = getattr(metrics, '_composite_score', None)
                if cs:
                    composites.append((name, cs.composite))
            if composites:
                composites.sort(key=lambda x: x[1], reverse=True)
                lines.append("### Composite Score Ranking")
                lines.append("")
                for rank, (name, score) in enumerate(composites, 1):
                    lines.append(f"{rank}. **{name}**: {score:.4f}")
                lines.append("")

        # Recommendations
        lines.append("## 6. Recommendations")
        lines.append("")
        lines.append("### Scenario-Based Pattern Selection")
        lines.append("")

        # Find best for each scenario
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

        lines.append(f"- **Complex Reasoning Tasks:** {best_success[0]} (highest success rate)")
        lines.append(f"- **Real-time/Low-latency Scenarios:** {best_speed[0]} (fastest response)")
        lines.append(f"- **Noisy/Unreliable Environments:** {best_robust[0]} (most robust)")
        lines.append(f"- **Enterprise/Compliance-critical:** {best_control[0]} (most controllable)")
        lines.append("")

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
        header += ",Trace Completeness,Policy Flag Rate,Resource Efficiency,Dim3,Dim4,Dim5,Dim6,Dim7,Composite"
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
            # E normalised scores
            ns = getattr(metrics, '_normalised_scores', None) if metrics else None
            cs = getattr(metrics, '_composite_score', None) if metrics else None
            d3 = f"{ns.dim3_action_decision_alignment:.4f}" if ns and ns.dim3_action_decision_alignment is not None else ""
            d4 = f"{ns.dim4_success_efficiency:.4f}" if ns and ns.dim4_success_efficiency is not None else ""
            d5 = f"{ns.dim5_behavioural_safety:.4f}" if ns and ns.dim5_behavioural_safety is not None else ""
            d6 = f"{ns.dim6_robustness_scalability:.4f}" if ns and ns.dim6_robustness_scalability is not None else ""
            d7 = f"{ns.dim7_controllability:.4f}" if ns and ns.dim7_controllability is not None else ""
            comp = f"{cs.composite:.4f}" if cs else ""
            line += f",{d3},{d4},{d5},{d6},{d7},{comp}"
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

