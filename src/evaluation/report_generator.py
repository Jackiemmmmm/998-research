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

        # Phase E: Normalised Dimension Scores
        has_normalised = any(
            getattr(m, '_normalised_scores', None) is not None
            for m in pattern_metrics.values()
        )
        if has_normalised:
            lines.append("## 5. Normalised Dimension Scores")
            lines.append("")
            lines.append("| Pattern | Dim 4 (Success) | Dim 6 (Robust) | Dim 7 (Control) | Composite |")
            lines.append("|---------|----------------|----------------|-----------------|-----------|")
            for name, metrics in pattern_metrics.items():
                ns = getattr(metrics, '_normalised_scores', None)
                cs = getattr(metrics, '_composite_score', None)
                d4 = f"{ns.dim4_success_efficiency:.3f}" if ns and ns.dim4_success_efficiency is not None else "N/A"
                d6 = f"{ns.dim6_robustness_scalability:.3f}" if ns and ns.dim6_robustness_scalability is not None else "N/A"
                d7 = f"{ns.dim7_controllability:.3f}" if ns and ns.dim7_controllability is not None else "N/A"
                comp = f"{cs.composite:.3f}" if cs else "N/A"
                lines.append(f"| {name:12s} | {d4:14s} | {d4:14s} | {d7:15s} | {comp:9s} |")
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
        lines.append("## 5. Recommendations")
        lines.append("")
        lines.append("### Scenario-Based Pattern Selection")
        lines.append("")

        # Find best for each scenario
        best_success = max(pattern_metrics.items(), key=lambda x: x[1].success.success_rate())
        best_speed = min(pattern_metrics.items(), key=lambda x: x[1].efficiency.avg_latency())
        best_robust = min(pattern_metrics.items(), key=lambda x: x[1].robustness.degradation_percentage)
        best_control = max(pattern_metrics.items(), key=lambda x: x[1].controllability.overall_controllability())

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
        header = "Pattern,Success Rate (Strict),Success Rate (Lenient),Controllability Gap,Avg Latency (s),Avg Tokens,Degradation (%),Controllability"
        # D2 + E columns
        header += ",Trace Completeness,Policy Flag Rate,Resource Efficiency,Dim4,Dim6,Dim7,Composite"
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
                f"{row['controllability']:.3f}"
            )
            # D2 sub-indicators
            cr = getattr(metrics, 'controllability_result', None) if metrics else None
            if cr:
                line += f",{cr.trace_completeness:.4f},{cr.policy_flag_rate:.4f},{cr.resource_efficiency:.4f}"
            else:
                line += ",,,"
            # E normalised scores
            ns = getattr(metrics, '_normalised_scores', None) if metrics else None
            cs = getattr(metrics, '_composite_score', None) if metrics else None
            d4 = f"{ns.dim4_success_efficiency:.4f}" if ns and ns.dim4_success_efficiency is not None else ""
            d6 = f"{ns.dim6_robustness_scalability:.4f}" if ns and ns.dim6_robustness_scalability is not None else ""
            d7 = f"{ns.dim7_controllability:.4f}" if ns and ns.dim7_controllability is not None else ""
            comp = f"{cs.composite:.4f}" if cs else ""
            line += f",{d4},{d6},{d7},{comp}"
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

