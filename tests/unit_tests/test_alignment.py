"""Unit tests for Phase C1 -- Dim3 Action-Decision Alignment.

Tests the AlignmentMetrics dataclass, the _collect_alignment_metrics
evaluator method, the LCS helper, and the compute_dim3_scores scoring
function.
"""

import pytest

from src.evaluation.metrics import AlignmentMetrics, PatternMetrics
from src.evaluation.scoring import compute_dim3_scores
from src.evaluation.evaluator import PatternEvaluator, TaskResult
from src.evaluation.test_suite import TestTask
from src.evaluation.trace import AgentTrace, StepRecord, StepType, ToolCallRecord


# ---------------------------------------------------------------------------
# AlignmentMetrics dataclass tests
# ---------------------------------------------------------------------------

class TestAlignmentMetrics:
    def test_default_values(self):
        """Default AlignmentMetrics should have zero values."""
        am = AlignmentMetrics()
        assert am.total_plan_tasks == 0
        assert am.total_aligned_tasks == 0
        assert am.plan_adherence_rate == 0.0
        assert am.any_tools_called is False
        assert am.overall_alignment() == 0.0

    def test_overall_alignment(self):
        """overall_alignment is mean of adherence, coverage, precision."""
        am = AlignmentMetrics(
            total_plan_tasks=4,
            plan_adherence_rate=0.75,
            avg_tool_coverage=0.8,
            avg_tool_precision=0.6,
        )
        expected = (0.75 + 0.8 + 0.6) / 3.0
        assert abs(am.overall_alignment() - expected) < 1e-9

    def test_overall_alignment_no_plan_tasks(self):
        """No plan tasks -> overall_alignment = 0.0."""
        am = AlignmentMetrics(total_plan_tasks=0)
        assert am.overall_alignment() == 0.0

    def test_to_dict(self):
        """to_dict should include all fields."""
        am = AlignmentMetrics(
            total_plan_tasks=2,
            total_aligned_tasks=1,
            plan_adherence_rate=0.5,
            avg_sequence_match=0.6,
            avg_tool_coverage=0.7,
            avg_tool_precision=0.8,
            task_alignment_scores={"C1": 0.9, "C2": 0.3},
            any_tools_called=True,
        )
        d = am.to_dict()
        assert d["total_plan_tasks"] == 2
        assert d["total_aligned_tasks"] == 1
        assert d["plan_adherence_rate"] == 0.5
        assert d["avg_sequence_match"] == 0.6
        assert d["avg_tool_coverage"] == 0.7
        assert d["avg_tool_precision"] == 0.8
        assert "overall_alignment" in d
        assert d["any_tools_called"] is True
        assert "C1" in d["task_alignment_scores"]


# ---------------------------------------------------------------------------
# LCS helper tests
# ---------------------------------------------------------------------------

class TestLongestCommonSubsequence:
    def test_identical_sequences(self):
        result = PatternEvaluator._longest_common_subsequence(
            ["a", "b", "c"], ["a", "b", "c"]
        )
        assert result == 3

    def test_no_overlap(self):
        result = PatternEvaluator._longest_common_subsequence(
            ["a", "b"], ["c", "d"]
        )
        assert result == 0

    def test_partial_overlap(self):
        result = PatternEvaluator._longest_common_subsequence(
            ["a", "b", "c"], ["a", "c"]
        )
        assert result == 2

    def test_empty_sequences(self):
        assert PatternEvaluator._longest_common_subsequence([], []) == 0
        assert PatternEvaluator._longest_common_subsequence(["a"], []) == 0
        assert PatternEvaluator._longest_common_subsequence([], ["b"]) == 0

    def test_subsequence_order(self):
        """LCS should respect ordering."""
        result = PatternEvaluator._longest_common_subsequence(
            ["weather_api", "calculator"], ["calculator", "weather_api"]
        )
        # Only one can match in order
        assert result == 1

    def test_repeated_elements(self):
        result = PatternEvaluator._longest_common_subsequence(
            ["a", "b", "a"], ["a", "a"]
        )
        assert result == 2


# ---------------------------------------------------------------------------
# _collect_alignment_metrics tests
# ---------------------------------------------------------------------------

def _make_trace_with_tools(task_id: str, tool_names: list) -> AgentTrace:
    """Helper to create an AgentTrace with specific tool calls."""
    trace = AgentTrace(pattern_name="test", task_id=task_id)
    step = StepRecord(
        step_index=0,
        step_type=StepType.ACT,
        content="action",
        tool_calls=[
            ToolCallRecord(tool_name=name, tool_args={}, tool_call_id=f"tc_{i}")
            for i, name in enumerate(tool_names)
        ],
    )
    trace.steps.append(step)
    trace.compute_aggregates()
    return trace


def _make_task_result(task_id: str, trace: AgentTrace = None) -> TaskResult:
    """Helper to create a TaskResult."""
    return TaskResult(
        task_id=task_id,
        task_category="tool",
        task_complexity="medium",
        pattern_name="test",
        success=True,
        trace=trace,
    )


def _make_test_task(task_id: str, plan: list = None) -> TestTask:
    """Helper to create a TestTask with a plan."""
    return TestTask(
        id=task_id,
        category="tool",
        prompt="test prompt",
        ground_truth=None,
        judge={"mode": "exact"},
        plan=plan,
    )


class TestCollectAlignmentMetrics:
    def setup_method(self):
        self.evaluator = PatternEvaluator()

    def test_perfect_alignment(self):
        """Agent calls exactly the planned tools in order."""
        tasks = [_make_test_task("C1", plan=["weather_api"])]
        trace = _make_trace_with_tools("C1", ["weather_api"])
        results = [_make_task_result("C1", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        assert am.total_aligned_tasks == 1
        assert am.any_tools_called is True
        assert abs(am.avg_tool_coverage - 1.0) < 1e-9
        assert abs(am.avg_tool_precision - 1.0) < 1e-9
        assert abs(am.avg_sequence_match - 1.0) < 1e-9
        assert abs(am.plan_adherence_rate - 1.0) < 1e-9

    def test_no_plan_tasks_skipped(self):
        """Tasks without plans should be skipped."""
        tasks = [_make_test_task("A1", plan=None)]
        trace = _make_trace_with_tools("A1", ["calculator"])
        results = [_make_task_result("A1", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 0

    def test_empty_plan_skipped(self):
        """Tasks with empty plan list should be skipped."""
        tasks = [_make_test_task("A1", plan=[])]
        trace = _make_trace_with_tools("A1", ["calculator"])
        results = [_make_task_result("A1", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 0

    def test_no_trace_skipped(self):
        """Tasks without a trace should be skipped."""
        tasks = [_make_test_task("C1", plan=["weather_api"])]
        results = [_make_task_result("C1", trace=None)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 0

    def test_no_actual_tools(self):
        """Agent made zero tool calls -> coverage=0, precision=0, any_tools_called=False."""
        tasks = [_make_test_task("C1", plan=["weather_api"])]
        trace = AgentTrace(pattern_name="test", task_id="C1")
        trace.steps.append(StepRecord(
            step_index=0, step_type=StepType.OUTPUT, content="answer"
        ))
        results = [_make_task_result("C1", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        assert am.any_tools_called is False
        assert abs(am.avg_tool_coverage - 0.0) < 1e-9
        assert abs(am.avg_tool_precision - 0.0) < 1e-9

    def test_extra_tools_reduce_precision(self):
        """Extra tools not in plan -> precision drops, coverage stays 1.0."""
        tasks = [_make_test_task("C1", plan=["weather_api"])]
        trace = _make_trace_with_tools("C1", ["weather_api", "calculator", "wiki_search"])
        results = [_make_task_result("C1", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        assert abs(am.avg_tool_coverage - 1.0) < 1e-9
        # precision = 1/3
        assert abs(am.avg_tool_precision - (1.0 / 3.0)) < 1e-9

    def test_multi_tool_plan(self):
        """Plan with multiple tools, all matched."""
        tasks = [_make_test_task("C2", plan=["fx_api", "calculator"])]
        trace = _make_trace_with_tools("C2", ["fx_api", "calculator"])
        results = [_make_task_result("C2", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        assert abs(am.avg_tool_coverage - 1.0) < 1e-9
        assert abs(am.avg_tool_precision - 1.0) < 1e-9
        assert abs(am.avg_sequence_match - 1.0) < 1e-9

    def test_mixed_tasks(self):
        """Mix of plan and no-plan tasks."""
        tasks = [
            _make_test_task("A1", plan=None),
            _make_test_task("C1", plan=["weather_api"]),
            _make_test_task("C2", plan=["fx_api", "calculator"]),
        ]
        results = [
            _make_task_result("A1", _make_trace_with_tools("A1", ["calc"])),
            _make_task_result("C1", _make_trace_with_tools("C1", ["weather_api"])),
            _make_task_result("C2", _make_trace_with_tools("C2", ["fx_api"])),
        ]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 2  # Only C1 and C2 have plans
        assert "C1" in am.task_alignment_scores
        assert "C2" in am.task_alignment_scores
        assert "A1" not in am.task_alignment_scores

    def test_adherence_threshold(self):
        """plan_adherence_rate counts tasks with score >= 0.5."""
        tasks = [
            _make_test_task("C1", plan=["weather_api"]),
            _make_test_task("C2", plan=["fx_api", "calculator"]),
        ]
        results = [
            # C1: perfect alignment -> score = 1.0 (>= 0.5)
            _make_task_result("C1", _make_trace_with_tools("C1", ["weather_api"])),
            # C2: no tools called -> score = 0.0 (< 0.5)
            _make_task_result("C2", AgentTrace(pattern_name="test", task_id="C2")),
        ]
        # Add an empty step to C2's trace so it's not totally empty
        results[1].trace.steps.append(
            StepRecord(step_index=0, step_type=StepType.OUTPUT, content="answer")
        )

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 2
        assert am.total_aligned_tasks == 1
        assert abs(am.plan_adherence_rate - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# compute_dim3_scores tests
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Verb-tool mapping tests
# ---------------------------------------------------------------------------

class TestVerbToolMapping:
    def test_expand_exact_tool_names_unchanged(self):
        """Exact tool names should pass through without expansion."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            ["weather_api", "calculator"],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == ["weather_api", "calculator"]

    def test_expand_verb_to_tools(self):
        """Verb 'search' should expand to wiki_search and shopping_search."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            ["search"],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == ["wiki_search", "shopping_search"]

    def test_expand_mixed_verbs_and_tools(self):
        """Mix of verbs and exact tool names."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            ["calculate", "weather_api"],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == ["calculator", "weather_api"]

    def test_expand_case_insensitive(self):
        """Verb lookup should be case-insensitive."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            ["Search", "CALCULATE"],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == ["wiki_search", "shopping_search", "calculator"]

    def test_expand_empty_plan(self):
        """Empty plan should return empty list."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            [],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == []

    def test_expand_unknown_verb_kept_as_is(self):
        """Unknown items should pass through unchanged."""
        result = PatternEvaluator._expand_plan_with_verb_mapping(
            ["unknown_verb"],
            PatternEvaluator.VERB_TOOL_MAP,
        )
        assert result == ["unknown_verb"]


class TestAlignmentWithVerbMapping:
    """Integration tests: verb-tool mapping in alignment scoring."""

    def setup_method(self):
        self.evaluator = PatternEvaluator()

    def test_verb_plan_matches_actual_tool(self):
        """Plan with verb 'search' should match actual 'wiki_search'."""
        tasks = [_make_test_task("C3", plan=["search"])]
        trace = _make_trace_with_tools("C3", ["wiki_search"])
        results = [_make_task_result("C3", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        # 'search' expands to ['wiki_search', 'shopping_search']
        # actual = ['wiki_search']
        # coverage = |{wiki_search, shopping_search} ∩ {wiki_search}| / |{wiki_search, shopping_search}| = 1/2
        assert abs(am.avg_tool_coverage - 0.5) < 1e-9
        # precision = |{wiki_search}| / |{wiki_search}| = 1.0
        assert abs(am.avg_tool_precision - 1.0) < 1e-9

    def test_verb_calculate_matches_calculator(self):
        """Plan with verb 'calculate' should match actual 'calculator'."""
        tasks = [_make_test_task("C2", plan=["convert", "calculate"])]
        trace = _make_trace_with_tools("C2", ["fx_api", "calculator"])
        results = [_make_task_result("C2", trace)]

        am = AlignmentMetrics()
        self.evaluator._collect_alignment_metrics(am, results, tasks)

        assert am.total_plan_tasks == 1
        # 'convert' -> ['fx_api'], 'calculate' -> ['calculator']
        # expanded plan = ['fx_api', 'calculator']
        # actual = ['fx_api', 'calculator']
        assert abs(am.avg_tool_coverage - 1.0) < 1e-9
        assert abs(am.avg_tool_precision - 1.0) < 1e-9
        assert abs(am.avg_sequence_match - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# compute_dim3_scores tests
# ---------------------------------------------------------------------------

class TestComputeDim3Scores:
    def test_no_plan_tasks_returns_none(self):
        """Pattern with no plan tasks -> Dim3 = None."""
        pm = PatternMetrics(pattern_name="test")
        scores = compute_dim3_scores({"test": pm})
        assert scores["test"] is None

    def test_with_alignment_data(self):
        """Dim3 should return overall_alignment value when tools were called."""
        pm = PatternMetrics(pattern_name="test")
        pm.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            plan_adherence_rate=0.75,
            avg_tool_coverage=0.8,
            avg_tool_precision=0.6,
            any_tools_called=True,
        )
        scores = compute_dim3_scores({"test": pm})
        expected = (0.75 + 0.8 + 0.6) / 3.0
        assert abs(scores["test"] - expected) < 1e-9

    def test_plan_tasks_but_no_tools_called_returns_none(self):
        """Pattern has plan tasks but never called any tools -> Dim3 = None."""
        pm = PatternMetrics(pattern_name="baseline")
        pm.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            plan_adherence_rate=0.0,
            avg_tool_coverage=0.0,
            avg_tool_precision=0.0,
            any_tools_called=False,
        )
        scores = compute_dim3_scores({"baseline": pm})
        assert scores["baseline"] is None

    def test_multiple_patterns(self):
        """Multiple patterns with different alignment data."""
        pm1 = PatternMetrics(pattern_name="react")
        pm1.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            plan_adherence_rate=1.0,
            avg_tool_coverage=1.0,
            avg_tool_precision=1.0,
            any_tools_called=True,
        )
        pm2 = PatternMetrics(pattern_name="cot")
        # No plan tasks for cot
        scores = compute_dim3_scores({"react": pm1, "cot": pm2})
        assert abs(scores["react"] - 1.0) < 1e-9
        assert scores["cot"] is None

    def test_multiple_patterns_with_no_tool_use(self):
        """Patterns with plan tasks but no tool calls get None, not 0.0."""
        pm_react = PatternMetrics(pattern_name="react")
        pm_react.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            plan_adherence_rate=1.0,
            avg_tool_coverage=1.0,
            avg_tool_precision=1.0,
            any_tools_called=True,
        )
        pm_baseline = PatternMetrics(pattern_name="baseline")
        pm_baseline.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            any_tools_called=False,
        )
        pm_reflex = PatternMetrics(pattern_name="reflex")
        pm_reflex.alignment = AlignmentMetrics(
            total_plan_tasks=4,
            any_tools_called=False,
        )
        scores = compute_dim3_scores({
            "react": pm_react,
            "baseline": pm_baseline,
            "reflex": pm_reflex,
        })
        assert abs(scores["react"] - 1.0) < 1e-9
        assert scores["baseline"] is None
        assert scores["reflex"] is None


# ---------------------------------------------------------------------------
# PatternMetrics integration tests
# ---------------------------------------------------------------------------

class TestPatternMetricsAlignment:
    def test_alignment_in_to_dict(self):
        """PatternMetrics.to_dict() should include alignment."""
        pm = PatternMetrics(pattern_name="test")
        d = pm.to_dict()
        assert "alignment" in d
        assert d["alignment"]["total_plan_tasks"] == 0

    def test_alignment_in_summary(self):
        """PatternMetrics.summary() should include alignment score."""
        pm = PatternMetrics(pattern_name="test")
        s = pm.summary()
        assert "alignment" in s
        assert s["alignment"] == 0.0
