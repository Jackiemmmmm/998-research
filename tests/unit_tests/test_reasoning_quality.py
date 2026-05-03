"""Unit tests for Phase B1 -- Reasoning Quality (Dimension 1).

Test cases from spec: docs/specs/week5-6_phase-b1_reasoning-quality.md
sections 7 (verification cases) and 5 (edge cases).
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from src.evaluation.metrics import PatternMetrics
from src.evaluation.reasoning_quality import (
    EXPECTED_MIN_THINK_STEPS,
    ReasoningExtractor,
    ReasoningJudge,
    ReasoningQualityResult,
    _aggregate_with_renormalisation,
    aggregate_cognitive_metrics,
    compute_self_consistency_score,
    compute_task_reasoning_quality,
    inject_self_consistency_scores,
)
from src.evaluation.scoring import compute_dim1_scores
from src.evaluation.test_suite import TestTask
from src.evaluation.trace import AgentTrace, StepRecord, StepType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace(
    *,
    pattern: str = "test",
    task_id: str = "T1",
    think_contents: Optional[List[str]] = None,
) -> AgentTrace:
    """Build an AgentTrace with the given THINK-step contents.

    The first step is INPUT (so the trace is realistic); each entry in
    ``think_contents`` becomes one THINK step in order.
    """
    steps: List[StepRecord] = []
    steps.append(StepRecord(
        step_index=0,
        step_type=StepType.INPUT,
        content="user prompt",
        message_type="human",
        stage_label="input",
    ))
    for i, content in enumerate(think_contents or []):
        steps.append(StepRecord(
            step_index=i + 1,
            step_type=StepType.THINK,
            content=content,
            message_type="ai",
            stage_label="think",
        ))
    trace = AgentTrace(pattern_name=pattern, task_id=task_id, steps=steps)
    trace.compute_aggregates()
    return trace


class _FakeResult:
    """Minimal stand-in for ``TaskResult`` used in unit tests."""

    def __init__(
        self,
        task_id: str,
        trace: Optional[AgentTrace] = None,
        output: str = "",
        judge_success: bool = False,
        lenient_judge_success: bool = False,
    ):
        self.task_id = task_id
        self.trace = trace
        self.output = output
        self.judge_success = judge_success
        self.lenient_judge_success = lenient_judge_success


class _ScriptedJudge(ReasoningJudge):
    """ReasoningJudge whose ``evaluate_coherence`` returns scripted values."""

    def __init__(
        self,
        coherence: float = 0.85,
        explanation: str = "scripted",
        used_fallback: bool = False,
        raise_on_call: bool = False,
    ):
        super().__init__(llm=object())  # avoid env-var lookup
        self._coherence = coherence
        self._explanation = explanation
        self._used_fallback = used_fallback
        self._raise = raise_on_call

    def evaluate_coherence(  # type: ignore[override]
        self,
        query: str,
        reasoning_steps,
        final_output: str,
    ):
        if self._raise:
            # Mirror the production fallback contract: never raise out
            # of evaluate_coherence even if the underlying LLM does.
            return 0.5, "fallback: scripted error", True
        return self._coherence, self._explanation, self._used_fallback


# ---------------------------------------------------------------------------
# ReasoningExtractor
# ---------------------------------------------------------------------------

class TestReasoningExtractor:
    def test_extracts_only_think_steps_in_order(self):
        trace = _make_trace(
            think_contents=["plan the work", "do the work", "double-check"],
        )
        steps = ReasoningExtractor.extract_reasoning_steps(trace)
        assert steps == ["plan the work", "do the work", "double-check"]

    def test_filters_implicit_reasoning_marker(self):
        """Synthetic ReAct marker '[implicit reasoning]' is dropped."""
        trace = _make_trace(
            think_contents=[
                "real thought",
                "[implicit reasoning]",
                "another real thought",
            ],
        )
        steps = ReasoningExtractor.extract_reasoning_steps(trace)
        assert steps == ["real thought", "another real thought"]

    def test_filters_empty_and_whitespace_content(self):
        trace = _make_trace(
            think_contents=["", "   ", "\n\n", "real one"],
        )
        steps = ReasoningExtractor.extract_reasoning_steps(trace)
        assert steps == ["real one"]

    def test_normalises_inner_whitespace(self):
        trace = _make_trace(
            think_contents=["multi  line\n\nwith  spaces"],
        )
        steps = ReasoningExtractor.extract_reasoning_steps(trace)
        assert steps == ["multi line with spaces"]

    def test_empty_trace_returns_empty_list(self):
        assert ReasoningExtractor.extract_reasoning_steps(
            _make_trace(think_contents=[])
        ) == []
        assert ReasoningExtractor.extract_reasoning_steps(None) == []


# ---------------------------------------------------------------------------
# Aggregation helper (_aggregate_with_renormalisation)
# ---------------------------------------------------------------------------

class TestAggregationRenormalisation:
    def test_single_run_renormalises_three_weights(self):
        # With self_consistency=None, weights renorm to
        # 0.20 / 0.5333 / 0.2667.
        score = _aggregate_with_renormalisation(
            coverage=1.0, coherence=0.0, agreement=0.0,
            self_consistency=None,
        )
        assert score == pytest.approx(0.20, abs=1e-4)

        score = _aggregate_with_renormalisation(
            coverage=0.0, coherence=1.0, agreement=0.0,
            self_consistency=None,
        )
        assert score == pytest.approx(0.5333, abs=1e-4)

        score = _aggregate_with_renormalisation(
            coverage=0.0, coherence=0.0, agreement=1.0,
            self_consistency=None,
        )
        assert score == pytest.approx(0.2667, abs=1e-4)

    def test_single_run_weights_sum_to_one(self):
        # Verify renormalised weights actually sum to ~1.
        score = _aggregate_with_renormalisation(
            coverage=1.0, coherence=1.0, agreement=1.0,
            self_consistency=None,
        )
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_multi_run_uses_full_four_weights(self):
        # With self_consistency=1.0, multi-run weights apply directly.
        score = _aggregate_with_renormalisation(
            coverage=1.0, coherence=0.85, agreement=1.0,
            self_consistency=1.0,
        )
        # 0.15*1 + 0.40*0.85 + 0.20*1 + 0.25*1 = 0.94
        assert score == pytest.approx(0.94, abs=1e-6)

    def test_clamps_to_unit_interval(self):
        score = _aggregate_with_renormalisation(
            coverage=2.0, coherence=2.0, agreement=2.0,
            self_consistency=2.0,
        )
        assert score == 1.0


# ---------------------------------------------------------------------------
# Spec verification cases (section 7 of the spec)
# ---------------------------------------------------------------------------

class TestSpecVerificationCases:
    """Verbatim numerical checks from spec section 7."""

    def test_case1_baseline_no_reasoning(self):
        """Spec Case 1: Baseline, 0 THINK steps, correct answer.

        Expected:
            think_step_count = 0
            missing_reasoning_trace = True
            trace_coverage = 0
            coherence_score = 0   (judge skipped)
            final_answer_agreement = 1.0
            self_consistency_score = None
            reasoning_quality_score = 0.2*0 + 0.5333*0 + 0.2667*1.0 = 0.2667
        """
        task = TestTask(
            id="A1",
            category="baseline",
            prompt="Compute 17 * 24.",
            ground_truth="408",
            judge={"mode": "exact"},
        )
        result = _FakeResult(
            task_id="A1",
            trace=_make_trace(think_contents=[]),
            output="408",
            judge_success=True,
            lenient_judge_success=True,
        )
        rq = compute_task_reasoning_quality(task, result, judge=None)
        assert rq.think_step_count == 0
        assert rq.missing_reasoning_trace is True
        assert rq.trace_coverage == 0.0
        assert rq.coherence_score == 0.0
        assert rq.final_answer_agreement == 1.0
        assert rq.self_consistency_score is None
        assert rq.reasoning_quality_score == pytest.approx(0.2667, abs=1e-4)

    def test_case2_cot_healthy_run(self):
        """Spec Case 2: 3 valid THINK steps, judge=0.85, correct answer.

        Expected reasoning_quality_score ~= 0.92.
        """
        task = TestTask(
            id="A1",
            category="baseline",
            prompt="Compute 17 * 24.",
            ground_truth="408",
            judge={"mode": "exact"},
        )
        result = _FakeResult(
            task_id="A1",
            trace=_make_trace(
                think_contents=[
                    "step 1: plan",
                    "step 2: compute",
                    "step 3: verify",
                ],
            ),
            output="408",
            judge_success=True,
            lenient_judge_success=True,
        )
        judge = _ScriptedJudge(coherence=0.85)
        rq = compute_task_reasoning_quality(task, result, judge=judge)

        assert rq.trace_coverage == pytest.approx(1.0)  # 3/2 capped to 1
        assert rq.coherence_score == pytest.approx(0.85)
        assert rq.final_answer_agreement == 1.0
        assert rq.self_consistency_score is None
        assert rq.judge_used_fallback is False
        # 0.20*1 + 0.5333*0.85 + 0.2667*1 ≈ 0.9200
        assert rq.reasoning_quality_score == pytest.approx(0.9200, abs=1e-4)

    def test_case3_judge_failure_lenient_success(self):
        """Spec Case 3: 2 THINK steps, judge fails, lenient-only answer.

        Expected:
            coherence_score = 0.5 (fallback)
            final_answer_agreement = 0.5
            reasoning_quality_score = 0.6
        """
        task = TestTask(
            id="A1",
            category="baseline",
            prompt="Compute 17 * 24.",
            ground_truth="408",
            judge={"mode": "exact"},
        )
        result = _FakeResult(
            task_id="A1",
            trace=_make_trace(
                think_contents=["plan", "execute"],
            ),
            output="408.0",
            judge_success=False,
            lenient_judge_success=True,
        )
        judge = ReasoningJudge(llm=_RaisingLLM())
        rq = compute_task_reasoning_quality(task, result, judge=judge)

        assert rq.trace_coverage == 1.0  # 2/2
        assert rq.coherence_score == 0.5
        assert rq.judge_used_fallback is True
        assert rq.final_answer_agreement == 0.5
        # 0.20*1.0 + 0.5333*0.5 + 0.2667*0.5 = 0.20 + 0.2667 + 0.1333 = 0.6
        assert rq.reasoning_quality_score == pytest.approx(0.6000, abs=1e-4)

    def test_case4_multi_run_full_agreement(self):
        """Spec Case 4: 3 runs all output '408'.

        Expected:
            self_consistency_score = 1.0
            reasoning_quality_score = 0.94
        """
        sc = compute_self_consistency_score(
            outputs=["408", "408", "408"],
            ground_truth="408",
            judge_config={"mode": "exact"},
        )
        assert sc == pytest.approx(1.0)

        score = _aggregate_with_renormalisation(
            coverage=1.0, coherence=0.85, agreement=1.0,
            self_consistency=sc,
        )
        # 0.15*1 + 0.40*0.85 + 0.20*1 + 0.25*1 = 0.94
        assert score == pytest.approx(0.94, abs=1e-6)

    def test_case5_multi_run_disagreement(self):
        """Spec Case 5: 3 runs, two agree (408, 408), one outlier (412).

        Expected: 2/3 ≈ 0.6667.
        """
        sc = compute_self_consistency_score(
            outputs=["408", "408", "412"],
            ground_truth="408",
            judge_config={"mode": "exact"},
        )
        assert sc == pytest.approx(2.0 / 3.0, abs=1e-6)

    def test_case6_json_mode_lenient_normalisation(self):
        """Spec Case 6: 3 runs, JSON with reordering + casing → all match."""
        outputs = [
            '{"name": "iPhone 15", "price": 999}',
            '{ "price": 999, "name": "iPhone 15" }',
            '{"name": "iphone 15", "price": 999}',
        ]
        sc = compute_self_consistency_score(
            outputs=outputs,
            ground_truth={"name": "iPhone 15", "price": 999},
            judge_config={"mode": "json"},
        )
        assert sc == pytest.approx(1.0)

    def test_case7_exact_mode_one_outlier(self):
        """Spec Case 7: extracted answers ['408','408','412'] → 2/3."""
        outputs = [
            "408",
            "The answer is 408.",
            "412",
        ]
        sc = compute_self_consistency_score(
            outputs=outputs,
            ground_truth="408",
            judge_config={"mode": "exact"},
        )
        assert sc == pytest.approx(2.0 / 3.0, abs=1e-6)


# ---------------------------------------------------------------------------
# compute_dim1_scores
# ---------------------------------------------------------------------------

class TestComputeDim1Scores:
    def test_returns_none_when_no_reasoning(self):
        pm = PatternMetrics(pattern_name="Baseline")
        # Defaults: total_tasks=0, tasks_with_reasoning=0
        scores = compute_dim1_scores({"Baseline": pm})
        assert scores == {"Baseline": None}

    def test_returns_none_when_total_zero_with_reasoning_zero(self):
        pm = PatternMetrics(pattern_name="P")
        pm.cognitive.total_tasks = 5
        pm.cognitive.tasks_with_reasoning = 0
        pm.cognitive.avg_reasoning_quality = 0.42  # would be ignored
        scores = compute_dim1_scores({"P": pm})
        assert scores["P"] is None

    def test_returns_avg_reasoning_quality_when_evaluable(self):
        pm = PatternMetrics(pattern_name="P")
        pm.cognitive.total_tasks = 4
        pm.cognitive.tasks_with_reasoning = 3
        pm.cognitive.avg_reasoning_quality = 0.77
        scores = compute_dim1_scores({"P": pm})
        assert scores["P"] == pytest.approx(0.77)

    def test_mixed_patterns(self):
        a = PatternMetrics(pattern_name="A")
        a.cognitive.total_tasks = 4
        a.cognitive.tasks_with_reasoning = 3
        a.cognitive.avg_reasoning_quality = 0.65

        b = PatternMetrics(pattern_name="B")  # all defaults

        scores = compute_dim1_scores({"A": a, "B": b})
        assert scores["A"] == pytest.approx(0.65)
        assert scores["B"] is None


# ---------------------------------------------------------------------------
# ReasoningJudge fallback path (mock LLM)
# ---------------------------------------------------------------------------

class _RaisingLLM:
    def invoke(self, *args, **kwargs):
        raise RuntimeError("network down")


class _BadJSONLLM:
    def invoke(self, *args, **kwargs):
        class _Resp:
            content = "not json at all"
        return _Resp()


class _GoodLLM:
    def __init__(self, payload: str):
        self._payload = payload

    def invoke(self, *args, **kwargs):
        class _Resp:
            content = self._payload  # type: ignore[assignment]
        # bind payload to instance attribute for the closure
        _Resp.content = self._payload
        return _Resp()


class TestReasoningJudgeFallback:
    def test_raises_to_fallback(self):
        judge = ReasoningJudge(llm=_RaisingLLM())
        score, expl, used_fallback = judge.evaluate_coherence(
            query="what is 2+2?",
            reasoning_steps=["think a bit"],
            final_output="4",
        )
        assert score == 0.5
        assert used_fallback is True
        assert "fallback" in expl.lower()

    def test_malformed_json_to_fallback(self):
        judge = ReasoningJudge(llm=_BadJSONLLM())
        score, expl, used_fallback = judge.evaluate_coherence(
            query="q", reasoning_steps=["s"], final_output="o",
        )
        assert score == 0.5
        assert used_fallback is True

    def test_well_formed_json_returns_mean(self):
        judge = ReasoningJudge(llm=_GoodLLM(
            payload='{"logical_progression": 0.8, "internal_consistency": 0.9, "explanation": "ok"}'
        ))
        score, expl, used_fallback = judge.evaluate_coherence(
            query="q", reasoning_steps=["s"], final_output="o",
        )
        assert score == pytest.approx(0.85)
        assert used_fallback is False
        assert expl == "ok"


# ---------------------------------------------------------------------------
# inject_self_consistency_scores edge cases
# ---------------------------------------------------------------------------

def _stub_rq_result(
    task_id: str,
    coverage: float = 1.0,
    coherence: float = 0.85,
    agreement: float = 1.0,
) -> ReasoningQualityResult:
    return ReasoningQualityResult(
        task_id=task_id,
        think_step_count=3,
        missing_reasoning_trace=False,
        trace_coverage=coverage,
        coherence_score=coherence,
        final_answer_agreement=agreement,
        self_consistency_score=None,
        reasoning_quality_score=_aggregate_with_renormalisation(
            coverage=coverage,
            coherence=coherence,
            agreement=agreement,
            self_consistency=None,
        ),
        judge_used_fallback=False,
        judge_explanation="seed",
    )


class TestInjectSelfConsistency:
    def test_single_run_is_noop(self):
        """One run per pattern -> nothing changes."""
        rq = _stub_rq_result("A1")
        original_score = rq.reasoning_quality_score
        pm = PatternMetrics(pattern_name="P")
        pm.cognitive = aggregate_cognitive_metrics([rq])

        inject_self_consistency_scores(
            per_pattern_runs={"P": [[rq]]},
            task_outputs={("P", "A1"): ["408"]},
            task_specs={
                "A1": TestTask(
                    id="A1",
                    category="baseline",
                    prompt="p",
                    ground_truth="408",
                    judge={"mode": "exact"},
                )
            },
            pattern_metrics={"P": pm},
        )

        assert rq.self_consistency_score is None
        assert rq.reasoning_quality_score == pytest.approx(original_score)

    def test_full_agreement_updates_latest_run(self):
        """3 runs all outputting '408' -> latest run gets sc=1.0 and 0.94."""
        runs = [
            [_stub_rq_result("A1")],
            [_stub_rq_result("A1")],
            [_stub_rq_result("A1")],
        ]
        pm = PatternMetrics(pattern_name="P")
        pm.cognitive = aggregate_cognitive_metrics(runs[-1])

        inject_self_consistency_scores(
            per_pattern_runs={"P": runs},
            task_outputs={("P", "A1"): ["408", "408", "408"]},
            task_specs={
                "A1": TestTask(
                    id="A1",
                    category="baseline",
                    prompt="p",
                    ground_truth="408",
                    judge={"mode": "exact"},
                )
            },
            pattern_metrics={"P": pm},
        )

        latest = runs[-1][0]
        assert latest.self_consistency_score == pytest.approx(1.0)
        assert latest.reasoning_quality_score == pytest.approx(0.94, abs=1e-6)

        # CognitiveMetrics refreshed.
        assert pm.cognitive.avg_self_consistency_score == pytest.approx(1.0)
        assert pm.cognitive.avg_reasoning_quality == pytest.approx(0.94, abs=1e-6)

    def test_prior_runs_not_mutated(self):
        """Earlier runs keep self_consistency_score=None (spec section 4.8)."""
        runs = [
            [_stub_rq_result("A1")],
            [_stub_rq_result("A1")],
        ]
        pm = PatternMetrics(pattern_name="P")
        pm.cognitive = aggregate_cognitive_metrics(runs[-1])

        inject_self_consistency_scores(
            per_pattern_runs={"P": runs},
            task_outputs={("P", "A1"): ["408", "412"]},
            task_specs={
                "A1": TestTask(
                    id="A1",
                    category="baseline",
                    prompt="p",
                    ground_truth="408",
                    judge={"mode": "exact"},
                )
            },
            pattern_metrics={"P": pm},
        )

        assert runs[0][0].self_consistency_score is None
        # latest run has sc=0.5 (largest class size 1, total 2)
        assert runs[1][0].self_consistency_score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# CognitiveMetrics aggregation edge cases
# ---------------------------------------------------------------------------

class TestCognitiveMetricsAggregation:
    def test_avg_self_consistency_none_when_all_none(self):
        rqs = [_stub_rq_result(f"T{i}") for i in range(3)]
        cog = aggregate_cognitive_metrics(rqs)
        assert cog.avg_self_consistency_score is None
        assert cog.tasks_with_reasoning == 3
        assert cog.total_tasks == 3

    def test_empty_input(self):
        cog = aggregate_cognitive_metrics([])
        assert cog.total_tasks == 0
        assert cog.tasks_with_reasoning == 0
        assert cog.avg_self_consistency_score is None

    def test_judge_fallback_count(self):
        rqs = [_stub_rq_result("A"), _stub_rq_result("B")]
        rqs[0].judge_used_fallback = True
        cog = aggregate_cognitive_metrics(rqs)
        assert cog.judge_fallback_count == 1


# ---------------------------------------------------------------------------
# Constants sanity checks (guardrails)
# ---------------------------------------------------------------------------

class TestConstants:
    def test_expected_min_think_steps(self):
        assert EXPECTED_MIN_THINK_STEPS == 2
