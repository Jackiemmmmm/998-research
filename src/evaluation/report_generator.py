"""
Report Generator - Generate evaluation reports
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .metrics import PatternMetrics, MetricsAggregator


class ReportGenerator:
    """Generate evaluation reports in various formats"""

    @staticmethod
    def generate_json_report(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate JSON report

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

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 JSON report saved to: {output_path}")

        return report

    @staticmethod
    def generate_markdown_report(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate Markdown report

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
        lines.append("| Pattern | Success Rate | Avg Latency (s) | Avg Tokens | Degradation (%) | Controllability |")
        lines.append("|---------|--------------|-----------------|------------|-----------------|-----------------|")

        for row in comparison["summary_table"]:
            lines.append(
                f"| {row['pattern']:12s} | "
                f"{row['success_rate']:12.1%} | "
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
            print(f"\n📄 Markdown report saved to: {output_path}")

        return markdown

    @staticmethod
    def generate_csv_comparison(
        pattern_metrics: Dict[str, PatternMetrics],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate CSV comparison table

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}
            output_path: Optional path to save CSV

        Returns:
            CSV string
        """
        comparison = MetricsAggregator.compare_patterns(pattern_metrics)

        # Build CSV
        lines = []
        lines.append("Pattern,Success Rate,Avg Latency (s),Avg Tokens,Degradation (%),Controllability")

        for row in comparison["summary_table"]:
            lines.append(
                f"{row['pattern']},"
                f"{row['success_rate']:.3f},"
                f"{row['avg_latency_sec']:.2f},"
                f"{row['avg_tokens']:.0f},"
                f"{row['degradation_pct']:.2f},"
                f"{row['controllability']:.3f}"
            )

        csv = "\n".join(lines)

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(csv)
            print(f"\n📄 CSV report saved to: {output_path}")

        return csv

    @staticmethod
    def print_console_report(pattern_metrics: Dict[str, PatternMetrics]):
        """Print a concise report to console"""
        comparison = MetricsAggregator.compare_patterns(pattern_metrics)

        print("\n" + "="*70)
        print(" " * 20 + "EVALUATION REPORT")
        print("="*70)

        # Summary table
        print("\n📊 SUMMARY COMPARISON")
        print("-"*70)
        print(f"{'Pattern':<15} {'Success':<10} {'Latency':<10} {'Tokens':<10} {'Robust':<10}")
        print("-"*70)

        for row in comparison["summary_table"]:
            print(
                f"{row['pattern']:<15} "
                f"{row['success_rate']:>8.1%}  "
                f"{row['avg_latency_sec']:>8.2f}s  "
                f"{row['avg_tokens']:>8.0f}  "
                f"{row['degradation_pct']:>7.1f}%"
            )

        print("-"*70)

        # Winners
        print("\n🏆 DIMENSION WINNERS")
        print("-"*70)
        print(f"Success:        {comparison['success_dimension']['best_pattern']:>15} "
              f"({comparison['success_dimension']['best_score']:.1%})")
        print(f"Efficiency:     {comparison['efficiency_dimension']['fastest_pattern']:>15} "
              f"({comparison['efficiency_dimension']['fastest_latency']:.2f}s)")
        print(f"Robustness:     {comparison['robustness_dimension']['most_robust_pattern']:>15} "
              f"({comparison['robustness_dimension']['lowest_degradation']:.1f}% degradation)")
        print(f"Controllability:{comparison['controllability_dimension']['most_controllable_pattern']:>15} "
              f"({comparison['controllability_dimension']['best_score']:.1%})")

        print("="*70 + "\n")
