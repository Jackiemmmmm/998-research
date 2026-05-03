"""Unit tests for Phase F -- Statistical Rigor & Reproducibility.

Test cases come from the spec section 8 verification cases:
``docs/specs/week5-6_phase-f_statistical-rigor.md``
"""

import math

import pytest

from src.evaluation.metrics import (
    ControllabilityMetrics,
    EfficiencyMetrics,
    PatternMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from src.evaluation.scoring import CompositeScore, NormalizedDimensionScores
from src.evaluation.statistics import (
    PatternRunRecord,
    aggregate_runs,
    compute_ci95,
    compute_cohens_d,
    compute_mean,
    compute_sample_std,
    flatten_pattern_metrics,
)


# ---------------------------------------------------------------------------
# Case 1: mean and sample standard deviation
# ---------------------------------------------------------------------------

class TestCase1MeanStd:
    def test_mean(self):
        """values = [0.60, 0.80, 1.00] -> mean = 0.80"""
        values = [0.60, 0.80, 1.00]
        assert compute_mean(values) == pytest.approx(0.80, rel=1e-3)

    def test_sample_std(self):
        """values = [0.60, 0.80, 1.00] -> sample std = 0.20"""
        values = [0.60, 0.80, 1.00]
        # sample variance = ((0.6-0.8)^2 + (0.8-0.8)^2 + (1.0-0.8)^2) / 2
        #                 = (0.04 + 0.0 + 0.04) / 2 = 0.04
        # sample std = sqrt(0.04) = 0.2
        assert compute_sample_std(values) == pytest.approx(0.20, rel=1e-3)

    def test_std_n1_returns_zero(self):
        """n=1 -> std = 0.0 (no variance defined)."""
        assert compute_sample_std([0.5]) == 0.0


# ---------------------------------------------------------------------------
# Case 2: 95% CI with n=3
# ---------------------------------------------------------------------------

class TestCase2CI95:
    def test_ci95_n3(self):
        """values = [0.60, 0.80, 1.00] -> CI = [0.304, 1.296].

        Note: the spec works through the math with intermediate
        rounding (``4.303 * 0.11547 = 0.496``); the unrounded
        margin is ``0.4969``, so CI is actually [0.3031, 1.2969].
        We assert to 3 decimal places (the spec's published
        precision) using ``abs=2e-3`` to absorb that rounding.
        """
        summary = compute_ci95([0.60, 0.80, 1.00])
        assert summary.n == 3
        assert summary.mean == pytest.approx(0.80, rel=1e-3)
        assert summary.std == pytest.approx(0.20, rel=1e-3)
        assert summary.ci95_low == pytest.approx(0.304, abs=2e-3)
        assert summary.ci95_high == pytest.approx(1.296, abs=2e-3)


# ---------------------------------------------------------------------------
# Case 3: zero-variance CI
# ---------------------------------------------------------------------------

class TestCase3ZeroVarianceCI:
    def test_identical_values(self):
        """values = [0.75, 0.75, 0.75] -> mean=0.75, std=0, CI collapses."""
        summary = compute_ci95([0.75, 0.75, 0.75])
        assert summary.mean == pytest.approx(0.75, rel=1e-3)
        assert summary.std == 0.0
        assert summary.ci95_low == pytest.approx(0.75, rel=1e-3)
        assert summary.ci95_high == pytest.approx(0.75, rel=1e-3)
        assert summary.n == 3

    def test_n_lt_2_collapses(self):
        """n < 2 -> CI = mean."""
        summary = compute_ci95([0.42])
        assert summary.mean == pytest.approx(0.42, rel=1e-3)
        assert summary.std == 0.0
        assert summary.ci95_low == pytest.approx(0.42, rel=1e-3)
        assert summary.ci95_high == pytest.approx(0.42, rel=1e-3)
        assert summary.n == 1


# ---------------------------------------------------------------------------
# Case 4: Cohen's d normal case
# ---------------------------------------------------------------------------

class TestCase4CohensD:
    def test_cohens_d_normal(self):
        """pattern_a=[0.80, 0.90, 1.00], pattern_b=[0.50, 0.60, 0.70] -> d = 3.0"""
        a = [0.80, 0.90, 1.00]
        b = [0.50, 0.60, 0.70]
        # mean_a = 0.9, mean_b = 0.6, std_a = 0.1, std_b = 0.1
        # pooled_var = (2*0.01 + 2*0.01)/4 = 0.01 -> pooled_std = 0.1
        # d = (0.9 - 0.6) / 0.1 = 3.0
        d = compute_cohens_d(a, b)
        assert d == pytest.approx(3.0, rel=1e-3)


# ---------------------------------------------------------------------------
# Case 5: Cohen's d zero-variance fallback
# ---------------------------------------------------------------------------

class TestCase5CohensDZeroVariance:
    def test_zero_variance_means_differ(self):
        """pattern_a all 0.80, pattern_b all 0.60 -> d = 999.0"""
        a = [0.80, 0.80, 0.80]
        b = [0.60, 0.60, 0.60]
        d = compute_cohens_d(a, b)
        assert d == pytest.approx(999.0, rel=1e-3)

    def test_zero_variance_means_equal(self):
        """Means equal AND std=0 -> d = 0.0"""
        d = compute_cohens_d([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        assert d == 0.0

    def test_zero_variance_negative(self):
        """If a < b under zero variance, returns -999.0."""
        a = [0.40, 0.40, 0.40]
        b = [0.60, 0.60, 0.60]
        d = compute_cohens_d(a, b)
        assert d == pytest.approx(-999.0, rel=1e-3)

    def test_never_returns_inf(self):
        """Spec: must NEVER return +/-inf even with degenerate input."""
        d = compute_cohens_d([1.0, 1.0], [0.0, 0.0])
        assert math.isfinite(d)


# ---------------------------------------------------------------------------
# Case 6: metric with None values
# ---------------------------------------------------------------------------

class TestCase6NoneHandling:
    def test_none_excluded_from_summary(self):
        """dim6 = [0.70, None, 0.90] -> summary built from [0.70, 0.90]."""
        # Build records with the dim6 series we want
        records = [
            _make_record("ReAct", run_index=1, dim6=0.70),
            _make_record("ReAct", run_index=2, dim6=None),
            _make_record("ReAct", run_index=3, dim6=0.90),
        ]
        report = aggregate_runs({"ReAct": records})
        stats = report.per_pattern["ReAct"]

        # dim6_robustness_scalability summary should be present and based
        # on the two non-None values.
        assert "dim6_robustness_scalability" in stats.summaries
        s = stats.summaries["dim6_robustness_scalability"]
        assert s.n == 2
        assert s.mean == pytest.approx(0.80, rel=1e-3)


# ---------------------------------------------------------------------------
# Case 7: run record flattening
# ---------------------------------------------------------------------------

class TestCase7Flattening:
    def test_react_flattening(self):
        """ReAct flattening: dim1 stays None; all other fields populated."""
        # Build PatternMetrics for ReAct matching the spec verification case.
        success = SuccessMetrics(
            total_tasks=8,
            successful_tasks=5,           # 5/8 = 0.625
            lenient_successful_tasks=6,    # 6/8 = 0.750
        )
        # Efficiency: latencies and tokens chosen so the means match the spec.
        # avg_latency requires the list be non-empty; use a single value.
        efficiency = EfficiencyMetrics(
            latencies=[4.8],
            input_tokens=[1000],
            output_tokens=[325],         # total = 1325
            step_counts=[2],
            tool_call_counts=[1],
        )
        # Spec value 1325.5 implies a half-token average; use two runs.
        efficiency = EfficiencyMetrics(
            latencies=[4.8],
            input_tokens=[1000, 1001],
            output_tokens=[325, 325],
            step_counts=[2],
            tool_call_counts=[1],
        )
        robustness = RobustnessMetrics()
        robustness.degradation_percentage = 25.0
        # overall_controllability() returns mean of available scores; we
        # bypass the underlying derivation by setting one input field
        # that yields 0.83.  Use format_compliance_rate alone -> mean = 0.83.
        controllability = ControllabilityMetrics(
            format_compliance_rate=0.83,
        )

        pm = PatternMetrics(
            pattern_name="ReAct",
            success=success,
            efficiency=efficiency,
            robustness=robustness,
            controllability=controllability,
        )

        ns = NormalizedDimensionScores(
            pattern_name="ReAct",
            dim1_reasoning_quality=None,  # Phase B1 reports None for ReAct
            dim3_action_decision_alignment=0.640,
            dim4_success_efficiency=0.741,
            dim5_behavioural_safety=0.910,
            dim6_robustness_scalability=0.618,
            dim7_controllability=0.801,
        )
        cs = CompositeScore(
            pattern_name="ReAct",
            dimension_scores={},
            weights={},
            composite=0.712,
            available_dimensions=6,
        )

        record = flatten_pattern_metrics(pm, ns, cs, run_index=1)

        assert record.run_index == 1
        assert record.pattern_name == "ReAct"
        assert record.success_rate_strict == pytest.approx(0.625, rel=1e-3)
        assert record.success_rate_lenient == pytest.approx(0.750, rel=1e-3)
        assert record.avg_latency_sec == pytest.approx(4.8, rel=1e-3)
        assert record.avg_total_tokens == pytest.approx(1325.5, rel=1e-3)
        assert record.degradation_percentage == pytest.approx(25.0, rel=1e-3)
        assert record.overall_controllability == pytest.approx(0.83, rel=1e-3)
        # dim1 stays None per Phase B1 behaviour for ReAct
        assert record.dim1_reasoning_quality is None
        assert record.dim3_action_decision_alignment == pytest.approx(0.640, rel=1e-3)
        assert record.dim4_success_efficiency == pytest.approx(0.741, rel=1e-3)
        assert record.dim5_behavioural_safety == pytest.approx(0.910, rel=1e-3)
        assert record.dim6_robustness_scalability == pytest.approx(0.618, rel=1e-3)
        assert record.dim7_controllability == pytest.approx(0.801, rel=1e-3)
        assert record.composite_score == pytest.approx(0.712, rel=1e-3)


# ---------------------------------------------------------------------------
# Case 8: all-None dimension excluded from summary
# ---------------------------------------------------------------------------

class TestCase8AllNoneOmitted:
    def test_all_none_metric_omitted(self):
        """3 runs with dim1=None for every run -> no dim1 summary."""
        records = [
            _make_record("ReAct", run_index=1, dim1=None),
            _make_record("ReAct", run_index=2, dim1=None),
            _make_record("ReAct", run_index=3, dim1=None),
        ]
        report = aggregate_runs({"ReAct": records})
        stats = report.per_pattern["ReAct"]

        # Spec section 6 + Case 8: all-None metric must be omitted.
        assert "dim1_reasoning_quality" not in stats.summaries

        # But the underlying run records keep the None values verbatim.
        assert all(r.dim1_reasoning_quality is None for r in stats.run_records)


# ---------------------------------------------------------------------------
# Additional defensive tests beyond the spec's eight cases
# ---------------------------------------------------------------------------

class TestPairwiseEffectSizes:
    def test_composite_pairwise_emitted(self):
        """aggregate_runs always emits composite_score effect sizes."""
        records_a = [_make_record("ReAct", run_index=i, composite=0.8) for i in (1, 2, 3)]
        records_b = [_make_record("Baseline", run_index=i, composite=0.5) for i in (1, 2, 3)]
        report = aggregate_runs({"ReAct": records_a, "Baseline": records_b})
        assert "composite_score" in report.pairwise_effect_sizes
        assert "success_rate_strict" in report.pairwise_effect_sizes
        # Two patterns -> exactly one directed pair per metric.
        assert len(report.pairwise_effect_sizes["composite_score"]) == 1


class TestUnequalRunCountsRefused:
    def test_uneven_runs_raise(self):
        """Spec 5.1: aggregate_runs must refuse if patterns have unequal run counts."""
        records_a = [_make_record("ReAct", run_index=i) for i in (1, 2, 3)]
        records_b = [_make_record("Baseline", run_index=i) for i in (1, 2)]
        with pytest.raises(ValueError):
            aggregate_runs({"ReAct": records_a, "Baseline": records_b})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    pattern_name: str,
    run_index: int,
    success_strict: float = 0.5,
    success_lenient: float = 0.6,
    latency: float = 4.0,
    tokens: float = 1000.0,
    degradation: float = 10.0,
    controllability: float = 0.7,
    dim1: float | None = 0.5,
    dim3: float | None = 0.6,
    dim4: float | None = 0.65,
    dim5: float | None = 0.7,
    dim6: float | None = 0.75,
    dim7: float | None = 0.8,
    composite: float | None = 0.7,
) -> PatternRunRecord:
    """Build a PatternRunRecord with defaults that are easy to override."""
    return PatternRunRecord(
        run_index=run_index,
        pattern_name=pattern_name,
        success_rate_strict=success_strict,
        success_rate_lenient=success_lenient,
        avg_latency_sec=latency,
        avg_total_tokens=tokens,
        degradation_percentage=degradation,
        overall_controllability=controllability,
        dim1_reasoning_quality=dim1,
        dim3_action_decision_alignment=dim3,
        dim4_success_efficiency=dim4,
        dim5_behavioural_safety=dim5,
        dim6_robustness_scalability=dim6,
        dim7_controllability=dim7,
        composite_score=composite,
    )
