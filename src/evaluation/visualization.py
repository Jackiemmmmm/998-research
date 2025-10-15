"""
Visualization module - Generate charts and plots for evaluation results
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

from .metrics import PatternMetrics


class EvaluationVisualizer:
    """Generate visualizations for pattern evaluation results"""

    def __init__(self, output_dir: str = "reports/figures"):
        """
        Initialize visualizer

        Args:
            output_dir: Directory to save figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

    def generate_all_plots(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> List[str]:
        """
        Generate all visualization plots

        Args:
            pattern_metrics: Dict of {pattern_name: PatternMetrics}

        Returns:
            List of generated file paths
        """
        generated_files = []

        print(f"\n📊 Generating visualizations...")

        # 1. Success rate comparison
        path = self.plot_success_rates(pattern_metrics)
        generated_files.append(path)

        # 2. Efficiency comparison
        path = self.plot_efficiency_comparison(pattern_metrics)
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

        print(f"✅ Generated {len(generated_files)} visualizations in {self.output_dir}")

        return generated_files

    def plot_success_rates(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot success rates comparison"""
        patterns = list(pattern_metrics.keys())
        success_rates = [metrics.success.success_rate() * 100 for metrics in pattern_metrics.values()]

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(patterns, success_rates, color=self.colors[:len(patterns)])

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold'
            )

        ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Pattern Success Rate Comparison', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "success_rate_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Success rate plot: {output_path}")
        return str(output_path)

    def plot_efficiency_comparison(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot efficiency metrics (latency and tokens)"""
        patterns = list(pattern_metrics.keys())
        latencies = [metrics.efficiency.avg_latency() for metrics in pattern_metrics.values()]
        tokens = [metrics.efficiency.avg_total_tokens() for metrics in pattern_metrics.values()]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Latency plot
        bars1 = ax1.bar(patterns, latencies, color=self.colors[:len(patterns)])
        for bar in bars1:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.2f}s',
                ha='center', va='bottom', fontsize=9
            )
        ax1.set_ylabel('Average Latency (seconds)', fontsize=11, fontweight='bold')
        ax1.set_title('Average Response Latency', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Token usage plot
        bars2 = ax2.bar(patterns, tokens, color=self.colors[:len(patterns)])
        for bar in bars2:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontsize=9
            )
        ax2.set_ylabel('Average Token Count', fontsize=11, fontweight='bold')
        ax2.set_title('Average Token Usage', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "efficiency_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Efficiency plot: {output_path}")
        return str(output_path)

    def plot_robustness(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot robustness metrics"""
        patterns = list(pattern_metrics.keys())
        original_rates = [metrics.robustness.original_success_rate * 100 for metrics in pattern_metrics.values()]
        perturbed_rates = [metrics.robustness.perturbed_success_rate * 100 for metrics in pattern_metrics.values()]

        x = np.arange(len(patterns))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 6))

        bars1 = ax.bar(x - width/2, original_rates, width, label='Original', color=self.colors[0])
        bars2 = ax.bar(x + width/2, perturbed_rates, width, label='Perturbed', color=self.colors[1])

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=8
                )

        ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Robustness: Original vs Perturbed Performance', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(patterns)
        ax.legend(fontsize=10)
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "robustness_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Robustness plot: {output_path}")
        return str(output_path)

    def plot_controllability(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot controllability metrics"""
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

        print(f"  ✓ Controllability plot: {output_path}")
        return str(output_path)

    def plot_radar_comparison(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot radar chart comparing all dimensions"""
        patterns = list(pattern_metrics.keys())

        # Prepare data (normalize to 0-100 scale)
        categories = ['Success', 'Efficiency\n(inverse latency)', 'Robustness', 'Controllability']
        N = len(categories)

        data = []
        for metrics in pattern_metrics.values():
            # Success: 0-100
            success = metrics.success.success_rate() * 100

            # Efficiency: inverse of latency, normalized (higher is better)
            # Assume max latency is 10s for normalization
            latency = metrics.efficiency.avg_latency()
            efficiency = max(0, (10 - latency) / 10 * 100)

            # Robustness: 100 - degradation percentage
            robustness = 100 - metrics.robustness.degradation_percentage

            # Controllability: 0-100
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

        print(f"  ✓ Radar chart: {output_path}")
        return str(output_path)

    def plot_success_by_category(
        self,
        pattern_metrics: Dict[str, PatternMetrics],
    ) -> str:
        """Plot success rates by task category"""
        patterns = list(pattern_metrics.keys())

        # Get all categories
        all_categories = set()
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

        print(f"  ✓ Success by category plot: {output_path}")
        return str(output_path)
