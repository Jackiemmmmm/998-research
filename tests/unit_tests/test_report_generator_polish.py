"""Unit tests for the post-2026-05-04 report-generator persistence polish.

These tests guarantee that the supervisor-facing rendering behaviours we
hand-edited into the markdown stay generated automatically by the code:

  1. ``_compute_dual_composite_ranking`` — single source of truth for
     View A (spec mean) + View B (all-7-dim, N/A=0) rankings.
  2. ``_render_executive_summary`` — auto-generated 5-section block at
     the top of the markdown report.
  3. Best-Pattern tie handling in § 1.
  4. "Deterministic across N=K" annotation when std=0.
  5. § 3 vs § 5 robustness ranking divergence detection.
  6. Dim 2 placeholder per-pattern table.

If any of these regress, supervisor-facing claims silently degrade —
hence the explicit unit coverage.
"""

from __future__ import annotations

from typing import Optional

import pytest

from src.evaluation.metrics import (
    AlignmentMetrics,
    BehaviouralSafetyMetrics,
    ControllabilityMetrics,
    EfficiencyMetrics,
    PatternMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from src.evaluation.reasoning_quality import CognitiveMetrics
from src.evaluation.report_generator import (
    ReportGenerator,
    _compute_dual_composite_ranking,
    _render_executive_summary,
)
from src.evaluation.scoring import CompositeScore, NormalizedDimensionScores
from src.evaluation.statistics import (
    PatternRunRecord,
    PatternStatistics,
    StatisticalReport,
    StatisticalSummary,
    aggregate_runs,
)


# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------

def _make_pattern_metrics(
    name: str,
    *,
    success_rate: float = 0.75,
    latency: float = 5.0,
    tokens: float = 500.0,
    degradation: float = 30.0,
    complexity_decline: float = 0.0,
    dim1: Optional[float] = None,
    dim3: Optional[float] = None,
    dim4: Optional[float] = 0.8,
    dim5: Optional[float] = 1.0,
    dim6: Optional[float] = 0.7,
    dim7: Optional[float] = 0.7,
    composite: float = 0.75,
    available_dims: int = 4,
) -> PatternMetrics:
    """Build a real PatternMetrics with enough fields for the renderer."""
    pm = PatternMetrics(pattern_name=name)
    # Success
    pm.success.total_tasks = 16
    pm.success.successful_tasks = int(round(success_rate * 16))
    pm.success.judge_pass_count = pm.success.successful_tasks
    pm.success.lenient_judge_pass_count = pm.success.successful_tasks
    # Efficiency
    pm.efficiency.task_latencies = [latency] * 16
    pm.efficiency.task_total_tokens = [int(tokens)] * 16
    pm.efficiency.task_step_counts = [3] * 16
    # Robustness
    pm.robustness.degradation_percentage = degradation
    pm.robustness.complexity_decline = complexity_decline
    pm.robustness.stability_index = 0.6
    pm.robustness.scaling_score = 1.0 - complexity_decline
    pm.robustness.original_success_rate = success_rate
    # Controllability
    pm.controllability.total_tasks = 16
    pm.controllability.tool_policy_compliant_tasks = 16
    pm.controllability.format_compliant_tasks = 12
    # Phase E + Phase F attachments
    pm._normalised_scores = NormalizedDimensionScores(
        pattern_name=name,
        dim1_reasoning_quality=dim1,
        dim2_cognitive_safety=None,  # Phase B2 placeholder
        dim3_action_decision_alignment=dim3,
        dim4_success_efficiency=dim4,
        dim5_behavioural_safety=dim5,
        dim6_robustness_scalability=dim6,
        dim7_controllability=dim7,
    )
    pm._composite_score = CompositeScore(
        pattern_name=name,
        dimension_scores={},
        weights={},
        composite=composite,
        available_dimensions=available_dims,
    )
    return pm


def _make_run_record(
    name: str,
    *,
    run_index: int = 1,
    success_strict: float = 0.75,
    composite: float = 0.75,
    dim1: Optional[float] = None,
    dim6: Optional[float] = 0.7,
    degradation: float = 30.0,
) -> PatternRunRecord:
    return PatternRunRecord(
        run_index=run_index,
        pattern_name=name,
        success_rate_strict=success_strict,
        success_rate_lenient=success_strict,
        avg_latency_sec=5.0,
        avg_total_tokens=500.0,
        degradation_percentage=degradation,
        overall_controllability=0.8,
        dim1_reasoning_quality=dim1,
        dim2_cognitive_safety=None,
        dim3_action_decision_alignment=None,
        dim4_success_efficiency=0.8,
        dim5_behavioural_safety=1.0,
        dim6_robustness_scalability=dim6,
        dim7_controllability=0.7,
        composite_score=composite,
    )


# ---------------------------------------------------------------------------
# 1. _compute_dual_composite_ranking
# ---------------------------------------------------------------------------

class TestDualCompositeRanking:
    def test_returns_none_when_no_composite_data(self):
        pm = PatternMetrics(pattern_name="X")  # no _composite_score
        result = _compute_dual_composite_ranking({"X": pm}, None)
        assert result is None

    def test_view_a_excludes_na_view_b_treats_na_as_zero(self):
        # Pattern A: 3 dims populated (high spec mean, but only 3/7).
        # Note: dim2 is always None in our model (Phase B2 placeholder).
        a = _make_pattern_metrics(
            "A",
            dim1=None, dim3=None,
            dim4=0.95, dim5=0.95, dim6=None, dim7=0.95,
            composite=0.95,
            available_dims=3,
        )
        # Pattern B: 5 dims populated, lower per-dim but more breadth.
        b = _make_pattern_metrics(
            "B",
            dim1=0.6, dim3=0.6, dim4=0.6, dim5=0.6, dim6=0.6, dim7=0.6,
            composite=0.6,
            available_dims=6,
        )
        result = _compute_dual_composite_ranking({"A": a, "B": b}, None)
        assert result is not None
        view_a = result["view_a_sorted"]
        view_b = result["view_b_sorted"]

        # View A: A wins (0.95) because its 3 dims are higher
        assert view_a[0][0] == "A"
        assert view_a[0][1] == pytest.approx(0.95)
        # View B: B wins because A's N/A → 0 drags A's all-7-mean down
        # A's all-7-mean = (0+0+0+0.95+0.95+0+0.95)/7 ≈ 0.40
        # B's all-7-mean = (0.6*6 + 0)/7 ≈ 0.51
        assert view_b[0][0] == "B"
        assert view_b[0][3] > view_a[0][3]

    def test_multi_run_overrides_with_phase_f_means(self):
        a = _make_pattern_metrics("A", dim4=0.5, composite=0.5)
        # Phase F says A's dim4 is actually 0.9 across runs
        records = [_make_run_record("A", run_index=i, composite=0.5) for i in (1, 2, 3)]
        for r in records:
            r.dim4_success_efficiency = 0.9
        report = aggregate_runs({"A": records})
        result = _compute_dual_composite_ranking({"A": a}, report)
        assert result is not None
        # View A reads from PatternMetrics._composite_score (not multi-run aware
        # in this layer), so check View B which uses the Phase F means.
        # All-7 mean override should pull dim4 from 0.5 → 0.9.
        # Sum over 7 dims with one populated at 0.9, rest 0 → 0.9/7 ≈ 0.1286.
        # We won't assert exact values, just that override happened:
        composite_entry = result["composites"][0]
        assert composite_entry[3] > 0.05  # post-override, not pre-override (0)


# ---------------------------------------------------------------------------
# 2. _render_executive_summary
# ---------------------------------------------------------------------------

class TestExecutiveSummary:
    def _build_minimal_multi_run_setup(self):
        """3 patterns × 3 runs, with one stochastic pattern."""
        # Pattern S: stochastic (varies across runs)
        s_records = [
            _make_run_record("Stoch", run_index=1, success_strict=0.7, composite=0.7),
            _make_run_record("Stoch", run_index=2, success_strict=0.8, composite=0.75),
            _make_run_record("Stoch", run_index=3, success_strict=0.9, composite=0.8),
        ]
        # Pattern D: deterministic (identical across runs)
        d_records = [
            _make_run_record("Det", run_index=i, success_strict=0.75, composite=0.85)
            for i in (1, 2, 3)
        ]
        # Pattern R: reasoning + tool user (has dim1 AND dim3)
        # so the "tool-using vs non-tool" caveat in § 4 has both sides.
        r_records = [
            _make_run_record("Reason", run_index=i, success_strict=0.6, composite=0.8, dim1=0.9)
            for i in (1, 2, 3)
        ]
        report = aggregate_runs({
            "Stoch": s_records, "Det": d_records, "Reason": r_records,
        })
        # Build single-run PatternMetrics for the renderer
        pms = {
            "Stoch": _make_pattern_metrics("Stoch", success_rate=0.9, composite=0.7,
                                           dim4=0.7, dim5=1.0, dim6=0.7, dim7=0.7),
            "Det": _make_pattern_metrics("Det", success_rate=0.75, composite=0.85,
                                         dim4=0.95, dim5=1.0, dim6=0.8, dim7=0.7,
                                         available_dims=4),
            "Reason": _make_pattern_metrics("Reason", success_rate=0.6, composite=0.8,
                                            dim1=0.9, dim3=0.95,  # ← tool user
                                            dim4=0.7, dim5=1.0, dim6=0.7, dim7=0.7,
                                            available_dims=6),
        }
        return pms, report

    def test_summary_contains_all_5_sections(self):
        pms, report = self._build_minimal_multi_run_setup()
        ranking = _compute_dual_composite_ranking(pms, report)
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        out = "\n".join(_render_executive_summary(pms, report, meta, ranking))

        assert "🎯 Executive Summary" in out
        assert "Multi-run statistical rigor" in out  # § 1
        assert "composite ranking flips" in out      # § 2
        assert "Reason leads on reasoning quality" in out  # § 3 (Reason has dim1=0.9)
        assert "Tool-using vs non-tool" in out        # § 4
        assert "Honest caveats" in out                # § 5

    def test_view_table_uses_dual_ranking(self):
        pms, report = self._build_minimal_multi_run_setup()
        ranking = _compute_dual_composite_ranking(pms, report)
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        out = "\n".join(_render_executive_summary(pms, report, meta, ranking))

        # Table should mention View A and View B with #1's
        assert "View | #1 | Last" in out
        assert "🥇" in out
        assert "Evaluable-dim mean" in out
        assert "All-7-dim mean" in out

    def test_dim2_caveat_fires_when_all_none(self):
        pms, report = self._build_minimal_multi_run_setup()
        # By construction every pattern has dim2 = None
        ranking = _compute_dual_composite_ranking(pms, report)
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        out = "\n".join(_render_executive_summary(pms, report, meta, ranking))
        assert "Dim 2 (Cognitive Safety)" in out
        assert "🚧 placeholder" in out

    def test_cohens_d_caveat_fires_on_low_std(self):
        # Build a setup where std(composite) < 0.01 for some pattern.
        # All Det runs have composite=0.85 → std=0.
        pms, report = self._build_minimal_multi_run_setup()
        ranking = _compute_dual_composite_ranking(pms, report)
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        out = "\n".join(_render_executive_summary(pms, report, meta, ranking))
        # "Det" has composite=0.85 in every run → std=0 → caveat must fire
        assert "Cohen's d auto-warning" in out


# ---------------------------------------------------------------------------
# 3. End-to-end markdown rendering smoke tests
# ---------------------------------------------------------------------------

class TestMarkdownPolishEndToEnd:
    def _full_setup(self):
        """6 patterns, 3 runs, deterministic + stochastic mix."""
        records_by_pattern = {}
        pms = {}
        # 5 deterministic patterns
        for name, sr, comp in [
            ("Baseline", 0.812, 0.85),
            ("ReAct", 0.625, 0.82),
            ("ReAct_Enhanced", 0.75, 0.72),
            ("CoT", 0.562, 0.68),
            ("Reflex", 0.75, 0.83),
        ]:
            recs = [
                _make_run_record(name, run_index=i, success_strict=sr, composite=comp)
                for i in (1, 2, 3)
            ]
            records_by_pattern[name] = recs
            # Match PatternMetrics single-run snapshot
            pms[name] = _make_pattern_metrics(
                name, success_rate=sr, composite=comp,
                dim1=0.78 if name in ("CoT",) else None,  # only CoT has reasoning
                dim4=0.8, dim5=1.0, dim6=0.7, dim7=0.7,
                available_dims=5 if name == "CoT" else 4,
            )
        # 1 stochastic pattern (ToT) — varies across runs
        tot_recs = [
            _make_run_record("ToT", run_index=1, success_strict=0.75, composite=0.78, dim1=0.88),
            _make_run_record("ToT", run_index=2, success_strict=0.81, composite=0.78, dim1=0.86),
            _make_run_record("ToT", run_index=3, success_strict=0.875, composite=0.78, dim1=0.90),
        ]
        records_by_pattern["ToT"] = tot_recs
        pms["ToT"] = _make_pattern_metrics(
            "ToT", success_rate=0.875, composite=0.78,
            dim1=0.90, dim4=0.6, dim5=1.0, dim6=0.7, dim7=0.77,
            available_dims=5,
        )
        report = aggregate_runs(records_by_pattern)
        return pms, report

    def test_markdown_contains_executive_summary_and_dual_views(self):
        pms, report = self._full_setup()
        meta = {
            "num_runs": 3,
            "judge_model": "qwen2.5:7b",
            "provider_model": {"provider": "ollama", "model": "llama3.1"},
            "git_branch": "main",
            "git_commit": "0" * 40,
        }
        md = ReportGenerator.generate_markdown_report(
            pms, output_path=None, statistical_report=report, run_metadata=meta,
        )
        # Executive summary appears once near the top
        assert "🎯 Executive Summary" in md
        # § 5 dual-view ranking still rendered
        assert "View A — Evaluable-dim mean" in md
        assert "View B — All-7-dim mean" in md
        # Dim 2 placeholder table rendered
        assert "Dim 2 -- Cognitive Safety" in md
        assert "🚧 pending" in md
        # Best Pattern uses multi-run mean; deterministic annotation present
        assert "Best Pattern (mean across N = 3 runs)" in md
        assert "deterministic across N=3" in md or "± 0.0 % (deterministic)" in md
        # § 3 cross-section note (data-aware)
        assert "Cross-section note" in md
        # Latest single run still mentioned for stochastic ToT
        assert "latest single run" in md.lower()

    def test_dim2_table_has_one_row_per_pattern(self):
        pms, report = self._full_setup()
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        md = ReportGenerator.generate_markdown_report(
            pms, output_path=None, statistical_report=report, run_metadata=meta,
        )
        # Each of the 6 patterns should appear in the Dim 2 placeholder table.
        # Match on the placeholder cell pattern that's unique to that table.
        placeholder_rows = md.count("🚧 pending | 🚧 pending | 🚧 pending | **N/A (Phase B2)**")
        assert placeholder_rows == 6

    def test_best_pattern_tie_handling(self):
        """When ToT mean and Baseline mean are within 0.5pp, output 'tied'."""
        # ToT mean across 3 runs = (0.75 + 0.81 + 0.875)/3 ≈ 0.812
        # Baseline = 0.812 deterministic → tie at 81.2%
        pms, report = self._full_setup()
        meta = {"num_runs": 3, "judge_model": "qwen2.5:7b"}
        md = ReportGenerator.generate_markdown_report(
            pms, output_path=None, statistical_report=report, run_metadata=meta,
        )
        # Should mention both names in the same Best Pattern line
        # find the line containing "Best Pattern (mean across"
        line = next(l for l in md.split("\n") if "Best Pattern (mean across" in l)
        assert "tied" in line or " and " in line
        # Both ToT and Baseline should appear
        assert "ToT" in line
        assert "Baseline" in line


# ---------------------------------------------------------------------------
# 4. Behaviour when single-run (multi_run=False)
# ---------------------------------------------------------------------------

class TestSingleRunBackwardCompat:
    def test_no_executive_summary_when_single_run(self):
        """Exec summary depends on multi-run -- omit cleanly otherwise."""
        pms = {"X": _make_pattern_metrics("X")}
        # No statistical_report = single-run mode
        md = ReportGenerator.generate_markdown_report(
            pms, output_path=None, statistical_report=None, run_metadata=None,
        )
        # Header must still render; exec summary must be absent
        assert "Agentic Pattern Evaluation Report" in md
        assert "🎯 Executive Summary" not in md
        # § 5 still rendered, but without a multi-run flag
        assert "Dimension Score Summary" in md or "## 5. Normalised" in md
