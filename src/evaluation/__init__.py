"""Evaluation Framework for Agentic Design Patterns.

Based on 7 dimensions: Reasoning Quality, Cognitive Safety, Action-Decision
Alignment, Success & Efficiency, Behavioural Safety, Robustness & Scalability,
Controllability, Transparency & Resource Efficiency.
"""

from .controllability import ControllabilityResult
from .evaluator import PatternEvaluator
from .metrics import (
    AlignmentMetrics,
    BehaviouralSafetyMetrics,
    ControllabilityMetrics,
    EfficiencyMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from .reasoning_quality import (
    CognitiveMetrics,
    ReasoningExtractor,
    ReasoningJudge,
    ReasoningQualityResult,
    compute_task_reasoning_quality,
    inject_self_consistency_scores,
)
from .report_generator import ReportGenerator
from .safety import check_content_safety, check_tool_compliance, compute_task_safety
from .scoring import CompositeScore, NormalizedDimensionScores, compute_dim1_scores
from .statistics import (
    PAIRWISE_EFFECT_SIZE_METRICS,
    T_CRITICAL_95,
    PairwiseEffectSize,
    PatternRunRecord,
    PatternStatistics,
    StatisticalReport,
    StatisticalSummary,
    aggregate_runs,
    compute_ci95,
    compute_cohens_d,
    compute_mean,
    compute_sample_std,
    flatten_pattern_metrics,
)
from .test_suite import TEST_SUITE, load_test_suite
from .trace import AgentTrace, StepRecord, StepType, TraceExtractor

__all__ = [
    "TEST_SUITE",
    "load_test_suite",
    "PatternEvaluator",
    "SuccessMetrics",
    "EfficiencyMetrics",
    "RobustnessMetrics",
    "ControllabilityMetrics",
    "AlignmentMetrics",
    "BehaviouralSafetyMetrics",
    "CognitiveMetrics",
    "ControllabilityResult",
    "ReasoningQualityResult",
    "ReasoningExtractor",
    "ReasoningJudge",
    "check_tool_compliance",
    "check_content_safety",
    "compute_task_safety",
    "compute_task_reasoning_quality",
    "compute_dim1_scores",
    "inject_self_consistency_scores",
    "NormalizedDimensionScores",
    "CompositeScore",
    # Phase F — statistical rigor
    "StatisticalSummary",
    "PairwiseEffectSize",
    "PatternRunRecord",
    "PatternStatistics",
    "StatisticalReport",
    "T_CRITICAL_95",
    "PAIRWISE_EFFECT_SIZE_METRICS",
    "compute_mean",
    "compute_sample_std",
    "compute_ci95",
    "compute_cohens_d",
    "flatten_pattern_metrics",
    "aggregate_runs",
    "ReportGenerator",
    "AgentTrace",
    "StepRecord",
    "StepType",
    "TraceExtractor",
]
