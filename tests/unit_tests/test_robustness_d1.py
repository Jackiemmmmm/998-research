"""Unit tests for Phase D1 — Enhanced Robustness & Scalability (Dim 6).

Test cases from spec: docs/specs/week3-4_phase-d1_robustness.md Section 9
"""

import pytest

from src.evaluation.metrics import RobustnessMetrics, PatternMetrics
from src.evaluation.scoring import compute_dim6_scores


# ---------------------------------------------------------------------------
# Verification Case 1: Absolute degradation
# ---------------------------------------------------------------------------

class TestAbsoluteDegradation:
    def test_case1(self):
        """S_clean=0.75, S_noisy=0.50 -> absolute_degradation=0.25"""
        rm = RobustnessMetrics(
            original_success_rate=0.75,
            perturbed_success_rate=0.50,
        )
        rm.calculate_degradation()
        assert abs(rm.absolute_degradation - 0.25) < 1e-9

    def test_no_degradation(self):
        """S_clean=0.80, S_noisy=0.80 -> absolute_degradation=0.0"""
        rm = RobustnessMetrics(
            original_success_rate=0.80,
            perturbed_success_rate=0.80,
        )
        rm.calculate_degradation()
        assert abs(rm.absolute_degradation - 0.0) < 1e-9

    def test_improvement(self):
        """S_clean=0.50, S_noisy=0.75 -> absolute_degradation=0.25 (abs value)"""
        rm = RobustnessMetrics(
            original_success_rate=0.50,
            perturbed_success_rate=0.75,
        )
        rm.calculate_degradation()
        assert abs(rm.absolute_degradation - 0.25) < 1e-9


# ---------------------------------------------------------------------------
# Verification Case 2: Percentage degradation
# ---------------------------------------------------------------------------

class TestPercentageDegradation:
    def test_case2(self):
        """S_clean=0.75, S_noisy=0.50 -> degradation_percentage=33.333..."""
        rm = RobustnessMetrics(
            original_success_rate=0.75,
            perturbed_success_rate=0.50,
        )
        rm.calculate_degradation()
        assert abs(rm.degradation_percentage - 33.333333) < 0.001

    def test_s_clean_zero(self):
        """S_clean=0 -> degradation_percentage=0.0 (edge case)."""
        rm = RobustnessMetrics(
            original_success_rate=0.0,
            perturbed_success_rate=0.0,
        )
        rm.calculate_degradation()
        assert rm.degradation_percentage == 0.0

    def test_full_degradation(self):
        """S_clean=1.0, S_noisy=0.0 -> degradation_percentage=100.0"""
        rm = RobustnessMetrics(
            original_success_rate=1.0,
            perturbed_success_rate=0.0,
        )
        rm.calculate_degradation()
        assert abs(rm.degradation_percentage - 100.0) < 1e-9

    def test_improvement_clamped_to_zero(self):
        """When S_noisy > S_clean, degradation is clamped to 0."""
        rm = RobustnessMetrics(
            original_success_rate=0.50,
            perturbed_success_rate=0.75,
        )
        rm.calculate_degradation()
        assert rm.degradation_percentage == 0.0


# ---------------------------------------------------------------------------
# Verification Case 3: Stability index
# ---------------------------------------------------------------------------

class TestStabilityIndex:
    def test_case3_single_task(self):
        """task variants=[1, 0, 1], p=2/3, variance=2/9, stability=1-8/9=1/9"""
        # p = 2/3, variance = (2/3)*(1/3) = 2/9
        # stability = 1 - (2/9) / (1/4) = 1 - 8/9 = 1/9
        p = 2.0 / 3.0
        variance = p * (1.0 - p)
        stability = 1.0 - min(variance / 0.25, 1.0)
        assert abs(stability - 1.0 / 9.0) < 1e-9

    def test_all_succeed(self):
        """All variants succeed -> p=1.0, variance=0, stability=1.0"""
        p = 1.0
        variance = p * (1.0 - p)
        stability = 1.0 - min(variance / 0.25, 1.0)
        assert abs(stability - 1.0) < 1e-9

    def test_all_fail(self):
        """All variants fail -> p=0.0, variance=0, stability=1.0"""
        p = 0.0
        variance = p * (1.0 - p)
        stability = 1.0 - min(variance / 0.25, 1.0)
        assert abs(stability - 1.0) < 1e-9

    def test_half_succeed(self):
        """p=0.5, variance=0.25, stability=1-1.0=0.0 (worst case)"""
        p = 0.5
        variance = p * (1.0 - p)
        stability = 1.0 - min(variance / 0.25, 1.0)
        assert abs(stability - 0.0) < 1e-9


# ---------------------------------------------------------------------------
# Verification Case 4: Complexity scaling
# ---------------------------------------------------------------------------

class TestComplexityScaling:
    def test_case4(self):
        """simple=0.90, complex=0.50 -> decline=0.40, scaling=0.60"""
        from src.evaluation.evaluator import _compute_complexity_decline
        success_by_complexity = {"simple": 0.90, "medium": 0.70, "complex": 0.50}
        decline = _compute_complexity_decline(success_by_complexity)
        assert abs(decline - 0.40) < 1e-9
        scaling = 1.0 - decline
        assert abs(scaling - 0.60) < 1e-9

    def test_no_decline(self):
        """simple=0.50, complex=0.50 -> decline=0.0, scaling=1.0"""
        from src.evaluation.evaluator import _compute_complexity_decline
        decline = _compute_complexity_decline({"simple": 0.50, "complex": 0.50})
        assert abs(decline - 0.0) < 1e-9

    def test_complex_better(self):
        """complex > simple -> decline clamped to 0.0"""
        from src.evaluation.evaluator import _compute_complexity_decline
        decline = _compute_complexity_decline({"simple": 0.30, "complex": 0.80})
        assert abs(decline - 0.0) < 1e-9

    def test_missing_simple(self):
        """No simple tasks -> decline=0.0, scaling=1.0"""
        from src.evaluation.evaluator import _compute_complexity_decline
        decline = _compute_complexity_decline({"medium": 0.50, "complex": 0.30})
        assert abs(decline - 0.0) < 1e-9

    def test_missing_complex(self):
        """No complex tasks -> decline=0.0, scaling=1.0"""
        from src.evaluation.evaluator import _compute_complexity_decline
        decline = _compute_complexity_decline({"simple": 0.90, "medium": 0.70})
        assert abs(decline - 0.0) < 1e-9


# ---------------------------------------------------------------------------
# Verification Case 5: Dim6 aggregation
# ---------------------------------------------------------------------------

class TestDim6Aggregation:
    def test_case5(self):
        """degradation=25%, stability=0.875, scaling=0.60 -> dim6=0.741666..."""
        rm = RobustnessMetrics(
            degradation_percentage=25.0,
            stability_index=0.875,
            scaling_score=0.60,
            perturbation_variant_count=5,  # non-zero so dim6 is computed
        )
        pm = PatternMetrics(pattern_name="test", robustness=rm)
        scores = compute_dim6_scores({"test": pm})
        expected = (0.75 + 0.875 + 0.60) / 3.0
        assert abs(scores["test"] - expected) < 1e-6
        assert abs(scores["test"] - 0.741666666) < 0.001

    def test_perfect_scores(self):
        """All perfect -> dim6=1.0"""
        rm = RobustnessMetrics(
            degradation_percentage=0.0,
            stability_index=1.0,
            scaling_score=1.0,
            perturbation_variant_count=3,
        )
        pm = PatternMetrics(pattern_name="test", robustness=rm)
        scores = compute_dim6_scores({"test": pm})
        assert abs(scores["test"] - 1.0) < 1e-9

    def test_worst_scores(self):
        """All worst -> dim6=0.0"""
        rm = RobustnessMetrics(
            degradation_percentage=100.0,
            stability_index=0.0,
            scaling_score=0.0,
            perturbation_variant_count=3,
        )
        pm = PatternMetrics(pattern_name="test", robustness=rm)
        scores = compute_dim6_scores({"test": pm})
        assert abs(scores["test"] - 0.0) < 1e-9


# ---------------------------------------------------------------------------
# Verification Case 6: No perturbations -> dim6=None
# ---------------------------------------------------------------------------

class TestDim6NoPerturbations:
    def test_case6(self):
        """perturbation_variant_count=0 -> dim6=None"""
        rm = RobustnessMetrics(perturbation_variant_count=0)
        pm = PatternMetrics(pattern_name="test", robustness=rm)
        scores = compute_dim6_scores({"test": pm})
        assert scores["test"] is None


# ---------------------------------------------------------------------------
# D1 dataclass defaults and backward compatibility
# ---------------------------------------------------------------------------

class TestRobustnessMetricsDefaults:
    def test_new_fields_have_defaults(self):
        """All new D1 fields have backward-compatible defaults."""
        rm = RobustnessMetrics()
        assert rm.perturbation_variant_count == 0
        assert rm.absolute_degradation == 0.0
        assert rm.stability_index == 0.0
        assert rm.success_by_complexity == {}
        assert rm.complexity_decline == 0.0
        assert rm.scaling_score == 1.0

    def test_to_dict_includes_d1_fields(self):
        """to_dict() includes all D1 fields."""
        rm = RobustnessMetrics(
            perturbation_variant_count=4,
            absolute_degradation=0.15,
            stability_index=0.8,
            success_by_complexity={"simple": 0.9, "complex": 0.5},
            complexity_decline=0.4,
            scaling_score=0.6,
        )
        d = rm.to_dict()
        assert "perturbation_variant_count" in d
        assert d["perturbation_variant_count"] == 4
        assert "absolute_degradation" in d
        assert abs(d["absolute_degradation"] - 0.15) < 1e-9
        assert "stability_index" in d
        assert abs(d["stability_index"] - 0.8) < 1e-9
        assert "success_by_complexity" in d
        assert "complexity_decline" in d
        assert "scaling_score" in d


# ---------------------------------------------------------------------------
# _compute_success_by_complexity helper
# ---------------------------------------------------------------------------

class TestComputeSuccessByComplexity:
    def test_basic(self):
        """Groups by complexity and computes success rates."""
        from src.evaluation.evaluator import _compute_success_by_complexity, TaskResult
        results = [
            TaskResult(task_id="A1", task_category="a", task_complexity="simple", judge_success=True, pattern_name="p"),
            TaskResult(task_id="A2", task_category="a", task_complexity="simple", judge_success=False, pattern_name="p"),
            TaskResult(task_id="B1", task_category="b", task_complexity="complex", judge_success=False, pattern_name="p"),
        ]
        sbc = _compute_success_by_complexity(results)
        assert abs(sbc["simple"] - 0.5) < 1e-9
        assert abs(sbc["complex"] - 0.0) < 1e-9
        assert "medium" not in sbc

    def test_empty_results(self):
        """Empty results -> empty dict."""
        from src.evaluation.evaluator import _compute_success_by_complexity
        sbc = _compute_success_by_complexity([])
        assert sbc == {}


# ---------------------------------------------------------------------------
# _collect_robustness_metrics integration test (via evaluator)
# ---------------------------------------------------------------------------

class TestCollectRobustnessMetrics:
    def test_all_perturbations_used(self):
        """Verify that all perturbation variants produce results, not just the first."""
        from src.evaluation.evaluator import PatternEvaluator, TaskResult
        evaluator = PatternEvaluator()

        original_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]
        # Simulate 2 perturbation results for task A1
        perturbed_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=False, pattern_name="p",
            ),
        ]

        rm = RobustnessMetrics(original_success_rate=1.0)
        evaluator._collect_robustness_metrics(rm, original_results, perturbed_results)

        assert rm.perturbation_variant_count == 2
        # Per-task robustness: orig succeeds, variant1 succeeds (1.0), variant2 fails (0.5)
        # mean = 0.75
        assert abs(rm.task_robustness_scores["A1"] - 0.75) < 1e-9
        # Perturbed success rate: 1/2 = 0.5
        assert abs(rm.perturbed_success_rate - 0.5) < 1e-9

    def test_no_perturbed_results(self):
        """No perturbed results -> perturbation_variant_count=0, scaling computed."""
        from src.evaluation.evaluator import PatternEvaluator, TaskResult
        evaluator = PatternEvaluator()

        original_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]

        rm = RobustnessMetrics(original_success_rate=1.0)
        evaluator._collect_robustness_metrics(rm, original_results, [])

        assert rm.perturbation_variant_count == 0
        assert rm.success_by_complexity == {"simple": 1.0}
        assert rm.scaling_score == 1.0

    def test_stability_index_with_multiple_tasks(self):
        """Stability index computed from tasks with > 2 variants."""
        from src.evaluation.evaluator import PatternEvaluator, TaskResult
        evaluator = PatternEvaluator()

        # Task A1: original=True, pert1=False, pert2=True -> [1,0,1], p=2/3
        # variance = 2/9, stability = 1 - (2/9)/0.25 = 1 - 8/9 = 1/9
        original_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]
        perturbed_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=False, pattern_name="p",
            ),
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]

        rm = RobustnessMetrics(original_success_rate=1.0)
        evaluator._collect_robustness_metrics(rm, original_results, perturbed_results)

        expected_stability = 1.0 / 9.0
        assert abs(rm.stability_index - expected_stability) < 1e-9

    def test_stability_excluded_for_single_variant(self):
        """Tasks with only 1 perturbation (success_vector len=2) excluded from stability."""
        from src.evaluation.evaluator import PatternEvaluator, TaskResult
        evaluator = PatternEvaluator()

        original_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]
        # Only one perturbation -> success_vector = [1, 0], len=2, not > 2
        perturbed_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=False, pattern_name="p",
            ),
        ]

        rm = RobustnessMetrics(original_success_rate=1.0)
        evaluator._collect_robustness_metrics(rm, original_results, perturbed_results)

        # stability_index should be 0.0 because no tasks qualify (need > 2 in vector)
        assert rm.stability_index == 0.0

    def test_all_variants_same_result_stability_is_one(self):
        """All variants succeed -> stability = 1.0 (variance = 0)."""
        from src.evaluation.evaluator import PatternEvaluator, TaskResult
        evaluator = PatternEvaluator()

        original_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]
        perturbed_results = [
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
            TaskResult(
                task_id="A1", task_category="a", task_complexity="simple",
                judge_success=True, pattern_name="p",
            ),
        ]

        rm = RobustnessMetrics(original_success_rate=1.0)
        evaluator._collect_robustness_metrics(rm, original_results, perturbed_results)

        assert abs(rm.stability_index - 1.0) < 1e-9
