"""Evaluation Framework for Agentic Design Patterns.

Based on 7 dimensions: Reasoning Quality, Cognitive Safety, Action-Decision
Alignment, Success & Efficiency, Behavioural Safety, Robustness & Scalability,
Controllability, Transparency & Resource Efficiency.
"""

from .evaluator import PatternEvaluator
from .metrics import (
    AlignmentMetrics,
    BehaviouralSafetyMetrics,
    ControllabilityMetrics,
    EfficiencyMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from .safety import check_tool_compliance, check_content_safety, compute_task_safety
from .controllability import ControllabilityResult
from .scoring import CompositeScore, NormalizedDimensionScores
from .report_generator import ReportGenerator
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
    "ControllabilityResult",
    "check_tool_compliance",
    "check_content_safety",
    "compute_task_safety",
    "NormalizedDimensionScores",
    "CompositeScore",
    "ReportGenerator",
    "AgentTrace",
    "StepRecord",
    "StepType",
    "TraceExtractor",
]
