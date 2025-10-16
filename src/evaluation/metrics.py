"""
Metrics module - Calculate evaluation metrics for 4 dimensions
1. Success: Task completion rate, accuracy
2. Efficiency: Latency, token usage, steps
3. Robustness: Performance under perturbations
4. Controllability: Schema compliance, tool policy adherence
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import statistics


@dataclass
class SuccessMetrics:
    """Success dimension metrics"""

    total_tasks: int = 0
    successful_tasks: int = 0  # Strict: exact match
    failed_tasks: int = 0
    partial_success_tasks: int = 0

    # Lenient evaluation (with answer extraction)
    lenient_successful_tasks: int = 0  # Lenient: after extracting answer

    # Per-category breakdown
    success_by_category: Dict[str, float] = field(default_factory=dict)
    success_by_complexity: Dict[str, float] = field(default_factory=dict)

    def success_rate(self) -> float:
        """Overall success rate (strict)"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def lenient_success_rate(self) -> float:
        """Overall success rate (lenient with answer extraction)"""
        if self.total_tasks == 0:
            return 0.0
        return self.lenient_successful_tasks / self.total_tasks

    def controllability_gap(self) -> float:
        """Gap between lenient and strict success (indicates output format control)"""
        return self.lenient_success_rate() - self.success_rate()

    def failure_rate(self) -> float:
        """Overall failure rate"""
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks_strict": self.successful_tasks,
            "successful_tasks_lenient": self.lenient_successful_tasks,
            "failed_tasks": self.failed_tasks,
            "partial_success_tasks": self.partial_success_tasks,
            "success_rate_strict": round(self.success_rate(), 3),
            "success_rate_lenient": round(self.lenient_success_rate(), 3),
            "controllability_gap": round(self.controllability_gap(), 3),
            "failure_rate": round(self.failure_rate(), 3),
            "success_by_category": {k: round(v, 3) for k, v in self.success_by_category.items()},
            "success_by_complexity": {k: round(v, 3) for k, v in self.success_by_complexity.items()},
        }


@dataclass
class EfficiencyMetrics:
    """Efficiency dimension metrics"""

    # Latency (seconds)
    latencies: List[float] = field(default_factory=list)

    # Token usage
    input_tokens: List[int] = field(default_factory=list)
    output_tokens: List[int] = field(default_factory=list)

    # Steps/iterations
    step_counts: List[int] = field(default_factory=list)

    # Tool calls
    tool_call_counts: List[int] = field(default_factory=list)

    def avg_latency(self) -> float:
        """Average latency in seconds"""
        return statistics.mean(self.latencies) if self.latencies else 0.0

    def median_latency(self) -> float:
        """Median latency in seconds"""
        return statistics.median(self.latencies) if self.latencies else 0.0

    def avg_total_tokens(self) -> float:
        """Average total token usage"""
        if not self.input_tokens or not self.output_tokens:
            return 0.0
        totals = [i + o for i, o in zip(self.input_tokens, self.output_tokens)]
        return statistics.mean(totals)

    def avg_steps(self) -> float:
        """Average number of steps"""
        return statistics.mean(self.step_counts) if self.step_counts else 0.0

    def avg_tool_calls(self) -> float:
        """Average number of tool calls"""
        return statistics.mean(self.tool_call_counts) if self.tool_call_counts else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "avg_latency_sec": round(self.avg_latency(), 2),
            "median_latency_sec": round(self.median_latency(), 2),
            "min_latency_sec": round(min(self.latencies), 2) if self.latencies else 0.0,
            "max_latency_sec": round(max(self.latencies), 2) if self.latencies else 0.0,
            "avg_total_tokens": round(self.avg_total_tokens(), 1),
            "total_input_tokens": sum(self.input_tokens),
            "total_output_tokens": sum(self.output_tokens),
            "avg_steps": round(self.avg_steps(), 1),
            "avg_tool_calls": round(self.avg_tool_calls(), 1),
            "total_tasks": len(self.latencies),
        }


@dataclass
class RobustnessMetrics:
    """Robustness dimension metrics"""

    # Original vs perturbed performance
    original_success_rate: float = 0.0
    perturbed_success_rate: float = 0.0

    # Performance degradation
    degradation_percentage: float = 0.0

    # Tool failure handling
    tool_failure_recovery_rate: float = 0.0
    tool_failure_graceful_degradation: float = 0.0

    # Per-task robustness
    task_robustness_scores: Dict[str, float] = field(default_factory=dict)

    def calculate_degradation(self):
        """Calculate performance degradation percentage"""
        if self.original_success_rate == 0:
            self.degradation_percentage = 0.0
        else:
            degradation = (self.original_success_rate - self.perturbed_success_rate) / self.original_success_rate
            self.degradation_percentage = degradation * 100

    def avg_robustness_score(self) -> float:
        """Average robustness score across tasks"""
        if not self.task_robustness_scores:
            return 0.0
        return statistics.mean(self.task_robustness_scores.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original_success_rate": round(self.original_success_rate, 3),
            "perturbed_success_rate": round(self.perturbed_success_rate, 3),
            "degradation_percentage": round(self.degradation_percentage, 2),
            "tool_failure_recovery_rate": round(self.tool_failure_recovery_rate, 3),
            "tool_failure_graceful_degradation": round(self.tool_failure_graceful_degradation, 3),
            "avg_robustness_score": round(self.avg_robustness_score(), 3),
            "task_robustness_scores": {k: round(v, 3) for k, v in self.task_robustness_scores.items()},
        }


@dataclass
class ControllabilityMetrics:
    """Controllability dimension metrics"""

    # Schema compliance
    total_json_tasks: int = 0
    schema_compliant_tasks: int = 0

    # Tool policy compliance
    total_tool_tasks: int = 0
    tool_policy_compliant_tasks: int = 0
    unauthorized_tool_uses: int = 0

    # Output format compliance
    format_compliance_rate: float = 0.0

    # Interpretability (from LLM judge if available)
    avg_interpretability_score: float = 0.0

    def schema_compliance_rate(self) -> float:
        """Schema compliance rate"""
        if self.total_json_tasks == 0:
            return 0.0
        return self.schema_compliant_tasks / self.total_json_tasks

    def tool_policy_compliance_rate(self) -> float:
        """Tool policy compliance rate"""
        if self.total_tool_tasks == 0:
            return 0.0
        return self.tool_policy_compliant_tasks / self.total_tool_tasks

    def overall_controllability(self) -> float:
        """Overall controllability score (0-1)"""
        scores = []

        if self.total_json_tasks > 0:
            scores.append(self.schema_compliance_rate())

        if self.total_tool_tasks > 0:
            scores.append(self.tool_policy_compliance_rate())

        scores.append(self.format_compliance_rate)

        if self.avg_interpretability_score > 0:
            scores.append(self.avg_interpretability_score / 10.0)  # Normalize to 0-1

        return statistics.mean(scores) if scores else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "schema_compliance_rate": round(self.schema_compliance_rate(), 3),
            "tool_policy_compliance_rate": round(self.tool_policy_compliance_rate(), 3),
            "format_compliance_rate": round(self.format_compliance_rate, 3),
            "avg_interpretability_score": round(self.avg_interpretability_score, 2),
            "overall_controllability": round(self.overall_controllability(), 3),
            "total_json_tasks": self.total_json_tasks,
            "schema_compliant_tasks": self.schema_compliant_tasks,
            "total_tool_tasks": self.total_tool_tasks,
            "tool_policy_compliant_tasks": self.tool_policy_compliant_tasks,
            "unauthorized_tool_uses": self.unauthorized_tool_uses,
        }


@dataclass
class PatternMetrics:
    """Complete metrics for a pattern across all dimensions"""

    pattern_name: str
    success: SuccessMetrics = field(default_factory=SuccessMetrics)
    efficiency: EfficiencyMetrics = field(default_factory=EfficiencyMetrics)
    robustness: RobustnessMetrics = field(default_factory=RobustnessMetrics)
    controllability: ControllabilityMetrics = field(default_factory=ControllabilityMetrics)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_name": self.pattern_name,
            "success": self.success.to_dict(),
            "efficiency": self.efficiency.to_dict(),
            "robustness": self.robustness.to_dict(),
            "controllability": self.controllability.to_dict(),
        }

    def summary(self) -> Dict[str, Any]:
        """Get summary metrics"""
        return {
            "pattern": self.pattern_name,
            "success_rate_strict": round(self.success.success_rate(), 3),
            "success_rate_lenient": round(self.success.lenient_success_rate(), 3),
            "controllability_gap": round(self.success.controllability_gap(), 3),
            "avg_latency_sec": round(self.efficiency.avg_latency(), 2),
            "avg_tokens": round(self.efficiency.avg_total_tokens(), 1),
            "degradation_pct": round(self.robustness.degradation_percentage, 2),
            "controllability": round(self.controllability.overall_controllability(), 3),
        }


class MetricsAggregator:
    """Aggregate and compare metrics across patterns"""

    @staticmethod
    def compare_patterns(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> Dict[str, Any]:
        """
        Compare patterns across all dimensions

        Returns a comparison report with winners in each dimension
        """
        if not pattern_metrics:
            return {}

        comparison = {
            "patterns": list(pattern_metrics.keys()),
            "success_dimension": MetricsAggregator._compare_success(pattern_metrics),
            "efficiency_dimension": MetricsAggregator._compare_efficiency(pattern_metrics),
            "robustness_dimension": MetricsAggregator._compare_robustness(pattern_metrics),
            "controllability_dimension": MetricsAggregator._compare_controllability(pattern_metrics),
            "summary_table": MetricsAggregator._build_summary_table(pattern_metrics),
        }

        return comparison

    @staticmethod
    def _compare_success(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> Dict[str, Any]:
        """Compare success rates"""
        success_rates = {
            name: metrics.success.success_rate()
            for name, metrics in pattern_metrics.items()
        }

        best_pattern = max(success_rates, key=success_rates.get)
        worst_pattern = min(success_rates, key=success_rates.get)

        return {
            "metric": "success_rate",
            "rates": {k: round(v, 3) for k, v in success_rates.items()},
            "best_pattern": best_pattern,
            "best_score": round(success_rates[best_pattern], 3),
            "worst_pattern": worst_pattern,
            "worst_score": round(success_rates[worst_pattern], 3),
        }

    @staticmethod
    def _compare_efficiency(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> Dict[str, Any]:
        """Compare efficiency (lower latency is better)"""
        latencies = {
            name: metrics.efficiency.avg_latency()
            for name, metrics in pattern_metrics.items()
        }

        fastest_pattern = min(latencies, key=latencies.get)
        slowest_pattern = max(latencies, key=latencies.get)

        return {
            "metric": "avg_latency_sec",
            "latencies": {k: round(v, 2) for k, v in latencies.items()},
            "fastest_pattern": fastest_pattern,
            "fastest_latency": round(latencies[fastest_pattern], 2),
            "slowest_pattern": slowest_pattern,
            "slowest_latency": round(latencies[slowest_pattern], 2),
        }

    @staticmethod
    def _compare_robustness(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> Dict[str, Any]:
        """Compare robustness (lower degradation is better)"""
        degradations = {
            name: metrics.robustness.degradation_percentage
            for name, metrics in pattern_metrics.items()
        }

        most_robust = min(degradations, key=degradations.get)
        least_robust = max(degradations, key=degradations.get)

        return {
            "metric": "degradation_percentage",
            "degradations": {k: round(v, 2) for k, v in degradations.items()},
            "most_robust_pattern": most_robust,
            "lowest_degradation": round(degradations[most_robust], 2),
            "least_robust_pattern": least_robust,
            "highest_degradation": round(degradations[least_robust], 2),
        }

    @staticmethod
    def _compare_controllability(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> Dict[str, Any]:
        """Compare controllability"""
        controllability_scores = {
            name: metrics.controllability.overall_controllability()
            for name, metrics in pattern_metrics.items()
        }

        most_controllable = max(controllability_scores, key=controllability_scores.get)
        least_controllable = min(controllability_scores, key=controllability_scores.get)

        return {
            "metric": "overall_controllability",
            "scores": {k: round(v, 3) for k, v in controllability_scores.items()},
            "most_controllable_pattern": most_controllable,
            "best_score": round(controllability_scores[most_controllable], 3),
            "least_controllable_pattern": least_controllable,
            "worst_score": round(controllability_scores[least_controllable], 3),
        }

    @staticmethod
    def _build_summary_table(
        pattern_metrics: Dict[str, PatternMetrics]
    ) -> List[Dict[str, Any]]:
        """Build summary comparison table"""
        return [metrics.summary() for metrics in pattern_metrics.values()]
