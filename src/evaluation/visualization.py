"""Visualization module - Generate charts and plots for evaluation results."""

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('Agg')  # Use non-interactive backend
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .metrics import PatternMetrics
from .scoring import NormalizedDimensionScores
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

        # 9. Trade-off scatter: reasoning quality (Dim 1) vs avg latency.
        #    Phase G P3 deliverable -- pairs with the radar / heatmap to
        #    expose cross-dimension trade-offs without re-reading tables.
        path = self.plot_tradeoff_reasoning_vs_efficiency(pattern_metrics)
        generated_files.append(path)

        # 10. Trade-off scatter: robustness (Dim 6) vs raw strict success.
        path = self.plot_tradeoff_robustness_vs_success(pattern_metrics)
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
            ('dim2_cognitive_safety', 'Dim 2\nCog Safety'),
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

    # ------------------------------------------------------------------
    # Phase G (Week 7-8 P3) -- regenerate figures from a saved JSON
    # ------------------------------------------------------------------

    @staticmethod
    def hydrate_pattern_metrics_from_json(
        evaluation_results: Dict[str, Any],
    ) -> Dict[str, PatternMetrics]:
        """Rebuild ``PatternMetrics`` objects from a saved results JSON.

        Used to regenerate the figure set against an existing
        ``evaluation_results.json`` (e.g. the Phase B2 final N=3 dataset)
        without re-running the multi-hour evaluation pipeline. Only the
        fields the visualization layer reads are populated; the JSON
        schema is the same one ``ReportGenerator.generate_json_report``
        emits.

        Args:
            evaluation_results: Parsed JSON with keys
                ``individual_metrics`` and ``normalised_dimension_scores``.

        Returns:
            Dict of ``{pattern_name: PatternMetrics}`` ordered to match
            the JSON's ``individual_metrics`` insertion order.
        """
        # Lazy imports keep this module importable even when callers do
        # not need the hydration path (avoids paying the full metrics
        # graph cost on simple ``import``s).
        from .metrics import (
            ControllabilityMetrics,
            EfficiencyMetrics,
            RobustnessMetrics,
            SuccessMetrics,
        )

        individual = evaluation_results.get("individual_metrics", {})
        normalised = evaluation_results.get("normalised_dimension_scores", {})

        rebuilt: Dict[str, PatternMetrics] = {}
        for name, blob in individual.items():
            pm = PatternMetrics(pattern_name=name)

            # --- Success ---------------------------------------------
            s = blob.get("success", {})
            success = SuccessMetrics()
            success.total_tasks = int(s.get("total_tasks", 0))
            success.successful_tasks = int(s.get("successful_tasks_strict", 0))
            success.lenient_successful_tasks = int(s.get("successful_tasks_lenient", 0))
            success.failed_tasks = int(s.get("failed_tasks", 0))
            success.partial_success_tasks = int(s.get("partial_success_tasks", 0))
            success.success_by_category = dict(s.get("success_by_category", {}))
            success.success_by_complexity = dict(s.get("success_by_complexity", {}))
            pm.success = success

            # --- Efficiency ------------------------------------------
            e = blob.get("efficiency", {})
            eff = EfficiencyMetrics()
            # The plotting layer reads avg_latency() / avg_total_tokens()
            # from the underlying lists; reconstruct minimal-length
            # sequences whose mean equals the saved aggregate.
            avg_lat = float(e.get("avg_latency_sec", 0.0))
            avg_tok = float(e.get("avg_total_tokens", 0.0))
            eff.latencies = [avg_lat]
            # Distribute total tokens 50/50 between in/out so the sum
            # round-trips through ``avg_total_tokens`` correctly.
            eff.input_tokens = [int(avg_tok / 2)]
            eff.output_tokens = [int(avg_tok - int(avg_tok / 2))]
            eff.step_counts = [int(round(float(e.get("avg_steps", 0))))]
            eff.tool_call_counts = [int(round(float(e.get("avg_tool_calls", 0))))]
            pm.efficiency = eff

            # --- Robustness ------------------------------------------
            r = blob.get("robustness", {})
            rob = RobustnessMetrics()
            rob.original_success_rate = float(r.get("original_success_rate", 0.0))
            rob.perturbed_success_rate = float(r.get("perturbed_success_rate", 0.0))
            rob.degradation_percentage = float(r.get("degradation_percentage", 0.0))
            rob.absolute_degradation = float(r.get("absolute_degradation", 0.0))
            rob.perturbation_variant_count = int(r.get("perturbation_variant_count", 0))
            rob.tool_failure_recovery_rate = float(r.get("tool_failure_recovery_rate", 0.0))
            rob.tool_failure_graceful_degradation = float(
                r.get("tool_failure_graceful_degradation", 0.0)
            )
            rob.stability_index = float(r.get("stability_index", 0.0))
            rob.success_by_complexity = dict(r.get("success_by_complexity", {}))
            rob.complexity_decline = float(r.get("complexity_decline", 0.0))
            rob.scaling_score = float(r.get("scaling_score", 1.0))
            rob.task_robustness_scores = dict(r.get("task_robustness_scores", {}))
            pm.robustness = rob

            # --- Controllability -------------------------------------
            c = blob.get("controllability", {})
            ctrl = ControllabilityMetrics()
            ctrl.total_json_tasks = int(c.get("total_json_tasks", 0))
            ctrl.schema_compliant_tasks = int(c.get("schema_compliant_tasks", 0))
            ctrl.total_tool_tasks = int(c.get("total_tool_tasks", 0))
            ctrl.tool_policy_compliant_tasks = int(c.get("tool_policy_compliant_tasks", 0))
            ctrl.unauthorized_tool_uses = int(c.get("unauthorized_tool_uses", 0))
            ctrl.format_compliance_rate = float(c.get("format_compliance_rate", 0.0))
            ctrl.avg_interpretability_score = float(c.get("avg_interpretability_score", 0.0))
            pm.controllability = ctrl

            # --- Normalised dimension scores (Phase E) ---------------
            ns_blob = normalised.get(name, {}).get("dimensions", {})
            ns = NormalizedDimensionScores(pattern_name=name)
            ns.dim1_reasoning_quality = ns_blob.get("dim1_reasoning_quality")
            ns.dim2_cognitive_safety = ns_blob.get("dim2_cognitive_safety")
            ns.dim3_action_decision_alignment = ns_blob.get("dim3_action_decision_alignment")
            ns.dim4_success_efficiency = ns_blob.get("dim4_success_efficiency")
            ns.dim5_behavioural_safety = ns_blob.get("dim5_behavioural_safety")
            ns.dim6_robustness_scalability = ns_blob.get("dim6_robustness_scalability")
            ns.dim7_controllability = ns_blob.get("dim7_controllability")
            # The visualisation layer reads ``_normalised_scores`` via
            # ``getattr`` -- attach it on the dataclass instance.
            pm._normalised_scores = ns  # type: ignore[attr-defined]

            rebuilt[name] = pm

        return rebuilt

    # ------------------------------------------------------------------
    # Phase G (Week 7-8 P3) -- trade-off scatter plots
    # ------------------------------------------------------------------

    def _annotate_points(
        self,
        ax: "plt.Axes",
        labels: List[str],
        xs: List[float],
        ys: List[float],
        x_offset: float = 0.0,
        y_offset: float = 0.0,
    ) -> None:
        """Annotate each scatter point with its pattern label.

        Uses a small offset so the text sits adjacent to the marker
        without overlapping it. Offsets are in data coordinates.
        """
        for label, x, y in zip(labels, xs, ys):
            ax.annotate(
                label,
                xy=(x, y),
                xytext=(x + x_offset, y + y_offset),
                fontsize=9,
                fontweight='bold',
                ha='left',
                va='bottom',
            )

    def plot_tradeoff_reasoning_vs_efficiency(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Scatter: Dim 1 reasoning quality vs avg latency (efficiency).

        X-axis: avg latency in seconds (log scale -- the sample range
        spans 2 s to 60 s on the N=3 dataset).
        Y-axis: Dim 1 reasoning quality (0-1).

        Patterns whose Dim 1 is None (no THINK trace -- Baseline / ReAct /
        ReAct_Enhanced on the current suite) are still plotted along
        ``y = 0`` with a hollow marker so the cost-of-no-reasoning
        trade-off is visible. They are annotated as "Dim 1 = N/A".

        Returns:
            Absolute path of the saved PNG.
        """
        patterns = list(pattern_metrics.keys())

        # Pull the same numbers the heatmap / composite use.
        latencies: List[float] = []
        dim1_scores: List[Optional[float]] = []
        for metrics in pattern_metrics.values():
            latencies.append(metrics.efficiency.avg_latency())
            ns = getattr(metrics, '_normalised_scores', None)
            dim1_scores.append(getattr(ns, 'dim1_reasoning_quality', None) if ns else None)

        # Split into "evaluable" (filled marker) and "N/A" (hollow at y=0).
        eval_x: List[float] = []
        eval_y: List[float] = []
        eval_labels: List[str] = []
        eval_colors: List[str] = []
        na_x: List[float] = []
        na_y: List[float] = []
        na_labels: List[str] = []
        na_colors: List[str] = []
        for i, name in enumerate(patterns):
            colour = self.colors[i % len(self.colors)]
            if dim1_scores[i] is None:
                na_x.append(latencies[i])
                na_y.append(0.0)
                na_labels.append(name)
                na_colors.append(colour)
            else:
                eval_x.append(latencies[i])
                eval_y.append(dim1_scores[i])
                eval_labels.append(name)
                eval_colors.append(colour)

        fig, ax = plt.subplots(figsize=(10, 6))

        if eval_x:
            ax.scatter(
                eval_x,
                eval_y,
                s=140,
                c=eval_colors,
                edgecolors='black',
                linewidths=0.8,
                zorder=3,
                label='Dim 1 evaluable',
            )
        if na_x:
            ax.scatter(
                na_x,
                na_y,
                s=140,
                facecolors='none',
                edgecolors=na_colors,
                linewidths=1.6,
                zorder=3,
                label='Dim 1 = N/A (no THINK trace)',
            )

        # Use a log x-axis only when the latency range is wide enough to
        # warrant it -- avoids squashing the 2 s -- 60 s sample.
        if latencies and max(latencies) / max(min(latencies), 1e-3) > 5:
            ax.set_xscale('log')

        # Annotation offsets in data coordinates -- small horizontal nudge
        # is fine on log scale because the offset is added before log-mapping.
        if eval_x:
            self._annotate_points(
                ax,
                eval_labels,
                eval_x,
                eval_y,
                x_offset=max(eval_x) * 0.02,
                y_offset=0.015,
            )
        if na_x:
            self._annotate_points(
                ax,
                [f'{lbl} (N/A)' for lbl in na_labels],
                na_x,
                na_y,
                x_offset=max(latencies) * 0.02 if latencies else 0.05,
                y_offset=0.025,
            )

        ax.set_xlabel('Average Latency (seconds, log scale)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Dim 1 Reasoning Quality (0–1)', fontsize=12, fontweight='bold')
        ax.set_title(
            'Reasoning Depth vs Efficiency Trade-off',
            fontsize=14,
            fontweight='bold',
        )
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, which='both', alpha=0.3)
        ax.legend(loc='lower right', fontsize=9, framealpha=0.9)

        plt.tight_layout()
        output_path = self.output_dir / "tradeoff_reasoning_vs_efficiency.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def plot_tradeoff_robustness_vs_success(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Scatter: Dim 6 robustness vs raw strict success rate.

        X-axis: strict success rate (0-1).
        Y-axis: Dim 6 robustness & scalability (0-1).
        Bubble size is scaled by perturbation degradation (%) so the
        third dimension of the trade-off is visible without stacking
        more axes; smaller bubbles = more robust under perturbation.

        Returns:
            Absolute path of the saved PNG.
        """
        patterns = list(pattern_metrics.keys())

        successes: List[float] = []
        dim6_scores: List[float] = []
        degradations: List[float] = []
        colours: List[str] = []
        for i, metrics in enumerate(pattern_metrics.values()):
            successes.append(metrics.success.success_rate())
            ns = getattr(metrics, '_normalised_scores', None)
            dim6_scores.append(getattr(ns, 'dim6_robustness_scalability', None) or 0.0)
            degradations.append(metrics.robustness.degradation_percentage)
            colours.append(self.colors[i % len(self.colors)])

        # Bubble size: linear map of degradation% to a marker area in
        # points^2.  Floor at 80 so a 0% degradation point is still
        # visible; ceiling implicit in the data (worst case ~60%).
        sizes = [80.0 + 8.0 * d for d in degradations]

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.scatter(
            successes,
            dim6_scores,
            s=sizes,
            c=colours,
            edgecolors='black',
            linewidths=0.8,
            alpha=0.85,
            zorder=3,
        )

        # Annotate -- small offset above and to the right of each point.
        self._annotate_points(
            ax,
            patterns,
            successes,
            dim6_scores,
            x_offset=0.012,
            y_offset=0.018,
        )

        ax.set_xlabel('Strict Success Rate (0–1)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Dim 6 Robustness & Scalability (0–1)', fontsize=12, fontweight='bold')
        ax.set_title(
            'Robustness vs Raw Success Trade-off (bubble size = degradation %)',
            fontsize=13,
            fontweight='bold',
        )
        ax.set_xlim(-0.02, 1.05)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(True, which='both', alpha=0.3)

        # Build a synthetic legend for the bubble-size encoding.
        legend_sizes = [10.0, 30.0, 50.0]
        legend_handles = [
            plt.scatter(
                [], [],
                s=80.0 + 8.0 * d,
                c='lightgray',
                edgecolors='black',
                linewidths=0.6,
                label=f'{int(d)}% degradation',
            )
            for d in legend_sizes
        ]
        ax.legend(
            handles=legend_handles,
            loc='lower left',
            fontsize=9,
            framealpha=0.9,
            title='Bubble size',
        )

        plt.tight_layout()
        output_path = self.output_dir / "tradeoff_robustness_vs_success.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)


def _regenerate_from_json(
    json_path: Path,
    output_dir: Path,
) -> List[str]:
    """Regenerate the figure set from a saved evaluation JSON (CLI helper).

    Reads ``evaluation_results.json`` (the schema written by
    ``ReportGenerator.generate_json_report``), hydrates ``PatternMetrics``
    and writes every figure ``EvaluationVisualizer.generate_all_plots``
    knows how to emit into ``output_dir``.

    Note: ``StatisticalReport`` is not reconstructed here -- that would
    require parsing the multi-run flatten format. As a result the
    multi-run-only ``composite_ci.png`` and CI overlays are skipped on
    this path. Single-run callers re-running ``run_evaluation.py`` still
    get the full Phase F treatment via the in-memory pipeline.
    """
    import json

    with open(json_path, encoding='utf-8') as fh:
        data = json.load(fh)

    pattern_metrics = EvaluationVisualizer.hydrate_pattern_metrics_from_json(data)
    visualizer = EvaluationVisualizer(output_dir=str(output_dir))
    return visualizer.generate_all_plots(pattern_metrics)


def main() -> None:
    r"""Regenerate figures from a saved evaluation JSON (CLI entrypoint).

    Usage:
        python -m src.evaluation.visualization \
            --from-json reports/phase_b2_final_n3_2026-05-08/evaluation_results.json \
            --output-dir reports/figures
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Regenerate evaluation figures from a saved results JSON.',
    )
    parser.add_argument(
        '--from-json',
        type=Path,
        required=True,
        help='Path to evaluation_results.json (Phase F multi-run snapshot).',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('reports/figures'),
        help='Directory to write the PNGs (default: reports/figures).',
    )
    args = parser.parse_args()

    paths = _regenerate_from_json(args.from_json, args.output_dir)
    # T201: print is intentional CLI output here.
    print(f"Wrote {len(paths)} figures to {args.output_dir}:")  # noqa: T201
    for p in paths:
        print(f"  - {p}")  # noqa: T201


if __name__ == '__main__':
    main()
