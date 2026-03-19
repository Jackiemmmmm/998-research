"""Unit tests for Phase E — Scoring (Normalisation + Composite) module.

Test cases from spec: docs/specs/week1-2_phase-e_normalisation.md § 6
Plus D2 Case 6 cross-validation test.
"""

import pytest

from src.evaluation.scoring import (
    normalize_min_max,
    compute_composite,
    compute_dim7_scores,
    NormalizedDimensionScores,
    CompositeScore,
    _safe_mean,
)
from src.evaluation.metrics import (
    PatternMetrics,
    SuccessMetrics,
    EfficiencyMetrics,
    RobustnessMetrics,
    ControllabilityMetrics,
)
from src.evaluation.controllability import ControllabilityResult


# ---------------------------------------------------------------------------
# Case 1: Min-max normalisation (unbounded indicator, inverted)
# ---------------------------------------------------------------------------

class TestNormalizeMinMax:
    def test_case1_latency(self):
        """latency [5, 10, 15] → inverted [1.0, 0.5, 0.0]"""
        result = normalize_min_max([5.0, 10.0, 15.0], invert=True)
        assert abs(result[0] - 1.0) < 1e-9
        assert abs(result[1] - 0.5) < 1e-9
        assert abs(result[2] - 0.0) < 1e-9

    def test_case2_all_same(self):
        """latency [8, 8, 8] → [1.0, 1.0, 1.0]"""
        result = normalize_min_max([8.0, 8.0, 8.0], invert=True)
        assert all(v == 1.0 for v in result)

    def test_single_value(self):
        """Single value → [1.0]"""
        result = normalize_min_max([42.0], invert=True)
        assert result == [1.0]

    def test_none_preserved(self):
        """None values preserved in output."""
        result = normalize_min_max([5.0, None, 15.0], invert=True)
        assert result[0] == 1.0
        assert result[1] is None
        assert result[2] == 0.0

    def test_non_inverted(self):
        """Non-inverted: [5, 10, 15] → [0.0, 0.5, 1.0]"""
        result = normalize_min_max([5.0, 10.0, 15.0], invert=False)
        assert abs(result[0] - 0.0) < 1e-9
        assert abs(result[1] - 0.5) < 1e-9
        assert abs(result[2] - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Case 3: Composite score with uniform weights (3 available dimensions)
# ---------------------------------------------------------------------------

class TestCompositeScore:
    def test_case3_three_dims(self):
        """dim4=0.8, dim6=0.6, dim7=0.7 → composite = 0.7"""
        nds = NormalizedDimensionScores(
            pattern_name="test",
            dim4_success_efficiency=0.8,
            dim6_robustness_scalability=0.6,
            dim7_controllability=0.7,
        )
        cs = compute_composite(nds)
        assert cs.available_dimensions == 3
        assert abs(cs.composite - 0.7) < 1e-9

    def test_case4_partial_availability(self):
        """dim4=0.8, dim6=None, dim7=0.7 → composite = 0.75"""
        nds = NormalizedDimensionScores(
            pattern_name="test",
            dim4_success_efficiency=0.8,
            dim6_robustness_scalability=None,
            dim7_controllability=0.7,
        )
        cs = compute_composite(nds)
        assert cs.available_dimensions == 2
        assert abs(cs.composite - 0.75) < 1e-9

    def test_no_dims(self):
        """All None → composite = 0.0, available = 0"""
        nds = NormalizedDimensionScores(pattern_name="test")
        cs = compute_composite(nds)
        assert cs.available_dimensions == 0
        assert cs.composite == 0.0

    def test_custom_weights(self):
        """Custom weights override uniform."""
        nds = NormalizedDimensionScores(
            pattern_name="test",
            dim4_success_efficiency=1.0,
            dim6_robustness_scalability=0.0,
        )
        # Weight dim4 at 3, dim6 at 1 → (3*1.0 + 1*0.0) / 4 = 0.75
        cs = compute_composite(nds, custom_weights={
            "dim4_success_efficiency": 3.0,
            "dim6_robustness_scalability": 1.0,
        })
        assert abs(cs.composite - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# Case 5: Dimension aggregation with missing sub-indicator
# ---------------------------------------------------------------------------

class TestDimensionAggregation:
    def test_case5_missing_sub_indicator(self):
        """norm_degradation=0.9, recovery_rate=None, robustness_score=0.6 → dim6 = 0.75"""
        # _safe_mean handles this
        result = _safe_mean([0.9, None, 0.6])
        assert abs(result - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# D2 Case 6: Cross-validation — Dim 7 full score
# ---------------------------------------------------------------------------

class TestDim7CrossValidation:
    def test_case6_dim7_full(self):
        """
        trace_completeness=0.6, policy_flag_rate=0.0, resource_efficiency=0.8,
        schema_compliance=0.9, format_compliance=0.7
        → dim7 = (1/5)*0.6 + (1/5)*1.0 + (1/5)*0.8 + (1/5)*0.9 + (1/5)*0.7 = 0.80
        """
        # Build PatternMetrics with controllability data
        cm = ControllabilityMetrics(
            total_json_tasks=4,
            schema_compliant_tasks=3,  # 3/4 = 0.75... no, need 0.9
        )
        # schema_compliance_rate = schema_compliant_tasks / total_json_tasks
        # Need 0.9, so: 9/10
        cm.total_json_tasks = 10
        cm.schema_compliant_tasks = 9
        cm.format_compliance_rate = 0.7

        pm = PatternMetrics(
            pattern_name="test_pattern",
            controllability=cm,
        )

        cr = ControllabilityResult(
            pattern_name="test_pattern",
            trace_completeness=0.6,
            tao_cycles=2,
            total_steps=10,
            policy_flag_rate=0.0,
            total_violations=0,
            tasks_with_violations=0,
            resource_efficiency=0.8,
        )

        pattern_metrics = {"test_pattern": pm}
        controllability_results = {"test_pattern": cr}

        dim7_scores = compute_dim7_scores(pattern_metrics, controllability_results)

        expected = (0.6 + 1.0 + 0.8 + 0.9 + 0.7) / 5.0  # = 0.8
        assert abs(dim7_scores["test_pattern"] - expected) < 1e-9
        assert abs(dim7_scores["test_pattern"] - 0.8) < 1e-9
