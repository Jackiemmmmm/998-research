"""Visualization module - Generate charts and plots for evaluation results."""

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('Agg')  # Use non-interactive backend
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .metrics import PatternMetrics
from .statistics import StatisticalReport


class EvaluationVisualizer:
    """Generate visualizations for pattern evaluation results."""

    def __init__(self, output_dir: str = "reports/figures"):
        """Initialize visualizer.

        Args:
            output_dir: Directory to save figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = ['#888888', '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E',
                       '#3D5A80', '#EE6C4D', '#293241', '#98C1D9']

    def generate_all_plots(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
        statistical_report: Optional[StatisticalReport] = None,
    ) -> List[str]:
        """Generate all visualization plots.

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}
            statistical_report: Optional Phase F multi-run aggregate.
                When supplied, ``plot_success_rates`` overlays 95 % CI
                error bars and an additional composite-score CI bar
                plot is emitted.  No-op for single-run.

        Returns:
            List of generated file paths
        """
        generated_files = []


        # 1. Success rate comparison (with CI error bars when available)
        path = self.plot_success_rates(pattern_metrics, statistical_report)
        generated_files.append(path)

        # 2. Efficiency comparison (with CI error bars when available)
        path = self.plot_efficiency_comparison(pattern_metrics, statistical_report)
        generated_files.append(path)

        # 3. Robustness comparison
        path = self.plot_robustness(pattern_metrics)
        generated_files.append(path)

        # 4. Controllability comparison
        path = self.plot_controllability(pattern_metrics)
        generated_files.append(path)

        # 5. Multi-dimension radar chart
        path = self.plot_radar_comparison(pattern_metrics)
        generated_files.append(path)

        # 6. Success by category
        path = self.plot_success_by_category(pattern_metrics)
        generated_files.append(path)

        # 7. Normalised dimension heatmap (Phase E)
        has_normalised = any(
            getattr(m, '_normalised_scores', None) is not None
            for m in pattern_metrics.values()
        )
        if has_normalised:
            path = self.plot_normalised_heatmap(pattern_metrics)
            generated_files.append(path)

        # 8. Composite-score CI bar plot (Phase F, multi-run only)
        if statistical_report is not None and statistical_report.num_runs > 1:
            path = self.plot_composite_ci(statistical_report)
            generated_files.append(path)

        return generated_files

    def plot_success_rates(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
        statistical_report: Optional[StatisticalReport] = None,
    ) -> str:
        """Plot success rates comparison.

        When ``statistical_report`` is supplied and reports multiple
        runs, overlays 95 % CI error bars on each bar.  Falls back to
        single-run rendering otherwise.
        """
        patterns = list(pattern_metrics.keys())
        success_rates = [metrics.success.success_rate() * 100 for metrics in pattern_metrics.values()]

        # Phase F: gather error-bar half-widths (in percent) when multi-run.
        yerr = None
        if statistical_report is not None and statistical_report.num_runs > 1:
            err_vals: List[float] = []
            for name in patterns:
                stats = statistical_report.per_pattern.get(name)
                if stats is None:
                    err_vals.append(0.0)
                    continue
                summary = stats.summaries.get("success_rate_strict")
                if summary is None:
                    err_vals.append(0.0)
                else:
                    err_vals.append((summary.ci95_high - summary.mean) * 100)
            yerr = err_vals

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(
            patterns,
            success_rates,
            color=self.colors[:len(patterns)],
            yerr=yerr,
            capsize=6 if yerr else 0,
            ecolor='black',
        )

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold'
            )

        ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        title = 'Pattern Success Rate Comparison'
        if yerr:
            title += f' (95 % CI, N = {statistical_report.num_runs})'
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "success_rate_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_efficiency_comparison(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
        statistical_report: Optional[StatisticalReport] = None,
    ) -> str:
        """Plot efficiency metrics (latency and tokens) with optional CI."""
        patterns = list(pattern_metrics.keys())
        latencies = [metrics.efficiency.avg_latency() for metrics in pattern_metrics.values()]
        tokens = [metrics.efficiency.avg_total_tokens() for metrics in pattern_metrics.values()]

        # Phase F error bars (multi-run only).
        yerr_lat = None
        yerr_tok = None
        if statistical_report is not None and statistical_report.num_runs > 1:
            yerr_lat = []
            yerr_tok = []
            for name in patterns:
                stats = statistical_report.per_pattern.get(name)
                if stats is None:
                    yerr_lat.append(0.0)
                    yerr_tok.append(0.0)
                    continue
                lat_s = stats.summaries.get("avg_latency_sec")
                tok_s = stats.summaries.get("avg_total_tokens")
                yerr_lat.append((lat_s.ci95_high - lat_s.mean) if lat_s else 0.0)
                yerr_tok.append((tok_s.ci95_high - tok_s.mean) if tok_s else 0.0)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Latency plot
        bars1 = ax1.bar(
            patterns,
            latencies,
            color=self.colors[:len(patterns)],
            yerr=yerr_lat,
            capsize=6 if yerr_lat else 0,
            ecolor='black',
        )
        for bar in bars1:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.2f}s',
                ha='center', va='bottom', fontsize=9
            )
        ax1.set_ylabel('Average Latency (seconds)', fontsize=11, fontweight='bold')
        title = 'Average Response Latency'
        if yerr_lat:
            title += f' (95 % CI, N = {statistical_report.num_runs})'
        ax1.set_title(title, fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Token usage plot
        bars2 = ax2.bar(
            patterns,
            tokens,
            color=self.colors[:len(patterns)],
            yerr=yerr_tok,
            capsize=6 if yerr_tok else 0,
            ecolor='black',
        )
        for bar in bars2:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontsize=9
            )
        ax2.set_ylabel('Average Token Count', fontsize=11, fontweight='bold')
        title2 = 'Average Token Usage'
        if yerr_tok:
            title2 += f' (95 % CI, N = {statistical_report.num_runs})'
        ax2.set_title(title2, fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "efficiency_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_composite_ci(
        self,
        statistical_report: StatisticalReport,
    ) -> str:
        """Bar plot of mean composite score with 95 % CI error bars.

        Phase F: only emitted when multi-run aggregation is active.
        """
        patterns: List[str] = []
        means: List[float] = []
        errs: List[float] = []
        for name, stats in statistical_report.per_pattern.items():
            summary = stats.summaries.get("composite_score")
            if summary is None:
                continue
            patterns.append(name)
            means.append(summary.mean)
            errs.append(summary.ci95_high - summary.mean)

        if not patterns:
            # Defensive: still produce a placeholder file so callers can
            # depend on a stable output path.
            output_path = self.output_dir / "composite_ci.png"
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No composite data", ha='center', va='center')
            ax.set_axis_off()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            return str(output_path)

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(
            patterns,
            means,
            color=self.colors[:len(patterns)],
            yerr=errs,
            capsize=6,
            ecolor='black',
        )
        for bar, mean in zip(bars, means):
            ax.text(
                bar.get_x() + bar.get_width() / 2., bar.get_height(),
                f'{mean:.3f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold'
            )
        ax.set_ylabel('Composite Score', fontsize=12, fontweight='bold')
        ax.set_title(
            f'Composite Score (mean ± 95 % CI, N = {statistical_report.num_runs})',
            fontsize=14, fontweight='bold',
        )
        ax.set_ylim(0, 1.05)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "composite_ci.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_robustness(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot robustness metrics with D1 stability and scaling indicators."""
        patterns = list(pattern_metrics.keys())
        original_rates = [metrics.robustness.original_success_rate * 100 for metrics in pattern_metrics.values()]
        perturbed_rates = [metrics.robustness.perturbed_success_rate * 100 for metrics in pattern_metrics.values()]

        # Check if D1 data is available
        has_d1 = any(
            metrics.robustness.perturbation_variant_count > 0
            for metrics in pattern_metrics.values()
        )

        if has_d1:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        else:
            fig, ax1 = plt.subplots(figsize=(10, 6))

        x = np.arange(len(patterns))
        width = 0.35

        bars1 = ax1.bar(x - width/2, original_rates, width, label='Original', color=self.colors[0])
        bars2 = ax1.bar(x + width/2, perturbed_rates, width, label='Perturbed', color=self.colors[1])

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=8
                )

        ax1.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax1.set_title('Original vs Perturbed Performance', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(patterns)
        ax1.legend(fontsize=10)
        ax1.set_ylim(0, 110)
        ax1.grid(axis='y', alpha=0.3)

        # D1 panel: stability index and scaling score
        if has_d1:
            stability = [metrics.robustness.stability_index * 100 for metrics in pattern_metrics.values()]
            scaling = [metrics.robustness.scaling_score * 100 for metrics in pattern_metrics.values()]

            bar_width = 0.35
            bars3 = ax2.bar(x - bar_width/2, stability, bar_width, label='Stability Index', color=self.colors[2])
            bars4 = ax2.bar(x + bar_width/2, scaling, bar_width, label='Scaling Score', color=self.colors[3])

            for bars in [bars3, bars4]:
                for bar in bars:
                    height = bar.get_height()
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom', fontsize=8
                    )

            ax2.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
            ax2.set_title('D1: Stability & Scaling', fontsize=12, fontweight='bold')
            ax2.set_xticks(x)
            ax2.set_xticklabels(patterns)
            ax2.legend(fontsize=10)
            ax2.set_ylim(0, 110)
            ax2.grid(axis='y', alpha=0.3)

        fig.suptitle('Robustness & Scalability (Dim 6)', fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        output_path = self.output_dir / "robustness_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_controllability(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot controllability metrics."""
        patterns = list(pattern_metrics.keys())
        schema_compliance = [
            metrics.controllability.schema_compliance_rate() * 100
            for metrics in pattern_metrics.values()
        ]
        overall_controllability = [
            metrics.controllability.overall_controllability() * 100
            for metrics in pattern_metrics.values()
        ]

        x = np.arange(len(patterns))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 6))

        bars1 = ax.bar(x - width/2, schema_compliance, width, label='Schema Compliance', color=self.colors[2])
        bars2 = ax.bar(x + width/2, overall_controllability, width, label='Overall Controllability', color=self.colors[3])

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom', fontsize=8
                    )

        ax.set_ylabel('Compliance Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Controllability Metrics', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(patterns)
        ax.legend(fontsize=10)
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "controllability_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_radar_comparison(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot radar chart comparing all dimensions.

        Uses Phase E normalised dimension scores if available (7-dim capable),
        otherwise falls back to raw 4-dimension comparison.
        """
        patterns = list(pattern_metrics.keys())

        # Try Phase E normalised scores first
        has_normalised = any(
            getattr(m, '_normalised_scores', None) is not None
            for m in pattern_metrics.values()
        )

        if has_normalised:
            # 7-dimension radar (show available dims)
            dim_labels = {
                'dim1_reasoning_quality': 'Dim1\nReasoning',
                'dim2_cognitive_safety': 'Dim2\nCog Safety',
                'dim3_action_decision_alignment': 'Dim3\nAlignment',
                'dim4_success_efficiency': 'Dim4\nSuccess',
                'dim5_behavioural_safety': 'Dim5\nBeh Safety',
                'dim6_robustness_scalability': 'Dim6\nRobustness',
                'dim7_controllability': 'Dim7\nControl',
            }

            # Determine which dims have data across any pattern
            active_dims = []
            for dim_key in dim_labels:
                for metrics in pattern_metrics.values():
                    ns = getattr(metrics, '_normalised_scores', None)
                    if ns and getattr(ns, dim_key, None) is not None:
                        active_dims.append(dim_key)
                        break

            if not active_dims:
                active_dims = ['dim4_success_efficiency', 'dim6_robustness_scalability', 'dim7_controllability']

            categories = [dim_labels[d] for d in active_dims]
            N = len(categories)

            data = []
            for metrics in pattern_metrics.values():
                ns = getattr(metrics, '_normalised_scores', None)
                row = []
                for dim_key in active_dims:
                    val = getattr(ns, dim_key, None) if ns else None
                    row.append((val or 0.0) * 100)
                data.append(row)
        else:
            # Fallback: raw 4-dimension
            categories = ['Success', 'Efficiency\n(inverse latency)', 'Robustness', 'Controllability']
            N = len(categories)

            data = []
            for metrics in pattern_metrics.values():
                success = metrics.success.success_rate() * 100
                latency = metrics.efficiency.avg_latency()
                efficiency = max(0, (10 - latency) / 10 * 100)
                robustness = 100 - metrics.robustness.degradation_percentage
                controllability = metrics.controllability.overall_controllability() * 100
                data.append([success, efficiency, robustness, controllability])

        # Radar chart
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        data_np = np.array(data)

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

        for i, (pattern, pattern_data) in enumerate(zip(patterns, data_np)):
            values = pattern_data.tolist()
            values += values[:1]  # Close the loop
            angles_plot = angles + angles[:1]

            ax.plot(angles_plot, values, 'o-', linewidth=2, label=pattern, color=self.colors[i])
            ax.fill(angles_plot, values, alpha=0.15, color=self.colors[i])

        ax.set_xticks(angles)
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
        ax.set_title('Multi-Dimension Pattern Comparison', fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        output_path = self.output_dir / "radar_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_normalised_heatmap(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot normalised dimension scores as a heatmap."""
        patterns = list(pattern_metrics.keys())

        dim_keys = [
            ('dim1_reasoning_quality', 'Dim 1\nReasoning'),
            ('dim3_action_decision_alignment', 'Dim 3\nAlignment'),
            ('dim4_success_efficiency', 'Dim 4\nSuccess'),
            ('dim5_behavioural_safety', 'Dim 5\nSafety'),
            ('dim6_robustness_scalability', 'Dim 6\nRobustness'),
            ('dim7_controllability', 'Dim 7\nControl'),
        ]

        # Build data matrix
        data = []
        for metrics in pattern_metrics.values():
            ns = getattr(metrics, '_normalised_scores', None)
            row = []
            for key, _ in dim_keys:
                val = getattr(ns, key, None) if ns else None
                row.append(val if val is not None else 0.0)
            data.append(row)

        data_np = np.array(data)
        dim_labels = [label for _, label in dim_keys]

        fig, ax = plt.subplots(figsize=(10, max(4, len(patterns) * 0.8)))

        im = ax.imshow(data_np, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

        # Annotations
        for i in range(len(patterns)):
            for j in range(len(dim_labels)):
                val = data_np[i, j]
                text_color = 'white' if val < 0.3 or val > 0.85 else 'black'
                ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                        fontsize=11, fontweight='bold', color=text_color)

        ax.set_xticks(np.arange(len(dim_labels)))
        ax.set_xticklabels(dim_labels, fontsize=10)
        ax.set_yticks(np.arange(len(patterns)))
        ax.set_yticklabels(patterns, fontsize=10)
        ax.set_title('Normalised Dimension Scores', fontsize=14, fontweight='bold')

        fig.colorbar(im, ax=ax, label='Score (0–1)', shrink=0.8)

        plt.tight_layout()
        output_path = self.output_dir / "normalised_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_success_by_category(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot success rates by task category."""
        patterns = list(pattern_metrics.keys())

        # Get all categories
        all_categories: set[str] = set()
        for metrics in pattern_metrics.values():
            all_categories.update(metrics.success.success_by_category.keys())

        categories = sorted(list(all_categories))

        # Prepare data
        data = []
        for metrics in pattern_metrics.values():
            category_rates = [
                metrics.success.success_by_category.get(cat, 0) * 100
                for cat in categories
            ]
            data.append(category_rates)

        # Plot grouped bar chart
        x = np.arange(len(categories))
        width = 0.8 / len(patterns)

        fig, ax = plt.subplots(figsize=(12, 6))

        for i, (pattern, pattern_data) in enumerate(zip(patterns, data)):
            offset = (i - len(patterns)/2 + 0.5) * width
            bars = ax.bar(x + offset, pattern_data, width, label=pattern, color=self.colors[i])

            # Add value labels (only if height > 5%)
            for bar in bars:
                height = bar.get_height()
                if height > 5:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2., height,
                        f'{height:.0f}',
                        ha='center', va='bottom', fontsize=7
                    )

        ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Success Rate by Task Category', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend(fontsize=10)
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "success_by_category.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)
