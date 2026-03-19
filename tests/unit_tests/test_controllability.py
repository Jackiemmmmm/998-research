"""Unit tests for Phase D2 — Controllability module.

Test cases from spec: docs/specs/week1-2_phase-d2_controllability.md § 6
"""

import pytest

from src.evaluation.trace import AgentTrace, StepRecord, StepType, ToolCallRecord
from src.evaluation.controllability import (
    compute_trace_completeness,
    compute_policy_violations,
    compute_resource_efficiency,
    ControllabilityResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace(step_types, tao_cycles=None, pattern="test", task_id="T1", tool_calls_map=None):
    """Create an AgentTrace with given step types."""
    steps = []
    for i, st in enumerate(step_types):
        tc_list = tool_calls_map.get(i, []) if tool_calls_map else []
        steps.append(StepRecord(
            step_index=i,
            step_type=st,
            content=f"step_{i}",
            tool_calls=tc_list,
        ))
    trace = AgentTrace(pattern_name=pattern, task_id=task_id, steps=steps)
    trace.compute_aggregates()
    if tao_cycles is not None:
        trace.tao_cycles = tao_cycles
    return trace


class _FakeTask:
    def __init__(self, task_id, policy=None):
        self.id = task_id
        self.policy = policy


class _FakeResult:
    def __init__(self, task_id, trace=None, success=True):
        self.task_id = task_id
        self.trace = trace
        self.success = success


# ---------------------------------------------------------------------------
# Case 1: ReAct trace with complete TAO cycles
# ---------------------------------------------------------------------------

class TestTraceCompleteness:
    def test_case1_react_trace(self):
        """10 steps, 2 TAO cycles → completeness = 0.6"""
        step_types = [
            StepType.INPUT,    # 0
            StepType.THINK,    # 1
            StepType.ACT,      # 2
            StepType.OBSERVE,  # 3
            StepType.THINK,    # 4
            StepType.ACT,      # 5
            StepType.OBSERVE,  # 6
            StepType.THINK,    # 7
            StepType.ACT,      # 8
            StepType.OUTPUT,   # 9
        ]
        trace = _make_trace(step_types)
        # trace.tao_cycles should be 2 (last THINK→ACT has no OBSERVE)
        assert trace.tao_cycles == 2

        avg_tc, _, _ = compute_trace_completeness([trace])
        assert abs(avg_tc - 0.6) < 1e-9

    def test_case2_reflex_no_tao(self):
        """3 steps, 0 TAO cycles → completeness = 0.0"""
        step_types = [StepType.INPUT, StepType.THINK, StepType.OUTPUT]
        trace = _make_trace(step_types)
        assert trace.tao_cycles == 0

        avg_tc, _, _ = compute_trace_completeness([trace])
        assert avg_tc == 0.0

    def test_empty_traces(self):
        """No traces → completeness = 0.0"""
        avg_tc, _, _ = compute_trace_completeness([])
        assert avg_tc == 0.0

    def test_multiple_traces_averaged(self):
        """Average across two traces."""
        # Trace 1: 6 steps, 2 TAO → 6/6 = 1.0
        t1 = _make_trace([
            StepType.THINK, StepType.ACT, StepType.OBSERVE,
            StepType.THINK, StepType.ACT, StepType.OBSERVE,
        ])
        assert t1.tao_cycles == 2
        # Trace 2: 3 steps, 0 TAO → 0.0
        t2 = _make_trace([StepType.INPUT, StepType.THINK, StepType.OUTPUT])

        avg_tc, _, _ = compute_trace_completeness([t1, t2])
        assert abs(avg_tc - 0.5) < 1e-9  # (1.0 + 0.0) / 2


# ---------------------------------------------------------------------------
# Case 3: Resource efficiency normalisation
# ---------------------------------------------------------------------------

class TestResourceEfficiency:
    def test_case3_four_patterns(self):
        """tokens [500, 1200, 3000, 800] → efficiency [1.0, 0.72, 0.0, 0.88]"""
        tokens = {"A": 500, "B": 1200, "C": 3000, "D": 800}
        result = compute_resource_efficiency(tokens)

        assert abs(result["A"] - 1.0) < 1e-9
        assert abs(result["B"] - 0.72) < 1e-9
        assert abs(result["C"] - 0.0) < 1e-9
        assert abs(result["D"] - 0.88) < 1e-9

    def test_all_same_tokens(self):
        """All same value → 1.0 for all."""
        tokens = {"A": 1000, "B": 1000, "C": 1000}
        result = compute_resource_efficiency(tokens)
        for v in result.values():
            assert v == 1.0

    def test_single_pattern(self):
        """Single pattern → 1.0."""
        result = compute_resource_efficiency({"A": 500})
        assert result["A"] == 1.0

    def test_empty(self):
        """No patterns → empty dict."""
        assert compute_resource_efficiency({}) == {}


# ---------------------------------------------------------------------------
# Cases 4 & 5: Policy violation detection
# ---------------------------------------------------------------------------

class TestPolicyViolations:
    def test_case4_no_violations(self):
        """All patterns have 0 violations, 4 tool tasks → flag_rate = 0.0"""
        tasks = [
            _FakeTask("C1", policy={"tool_whitelist": ["weather_api"]}),
            _FakeTask("C2", policy={"tool_whitelist": ["fx_api", "calculator"]}),
            _FakeTask("C3", policy={"tool_whitelist": ["wiki_search"]}),
            _FakeTask("C4", policy={"tool_whitelist": ["shopping_search"]}),
        ]
        results = [
            _FakeResult("C1", trace=_make_trace(
                [StepType.ACT], tool_calls_map={0: [
                    ToolCallRecord(tool_name="weather_api", tool_args={}, tool_call_id="1")
                ]}
            )),
            _FakeResult("C2", trace=_make_trace(
                [StepType.ACT], tool_calls_map={0: [
                    ToolCallRecord(tool_name="fx_api", tool_args={}, tool_call_id="2")
                ]}
            )),
            _FakeResult("C3", trace=_make_trace(
                [StepType.ACT], tool_calls_map={0: [
                    ToolCallRecord(tool_name="wiki_search", tool_args={}, tool_call_id="3")
                ]}
            )),
            _FakeResult("C4", trace=_make_trace(
                [StepType.ACT], tool_calls_map={0: [
                    ToolCallRecord(tool_name="shopping_search", tool_args={}, tool_call_id="4")
                ]}
            )),
        ]

        flag_rate, total_v, tasks_v = compute_policy_violations(results, tasks)
        assert flag_rate == 0.0
        assert total_v == 0
        assert tasks_v == 0

    def test_case5_violation_detected(self):
        """C1 has 1 violation ('calculator' not in whitelist), C2 has 0 → flag_rate = 0.5"""
        tasks = [
            _FakeTask("C1", policy={"tool_whitelist": ["weather_api"]}),
            _FakeTask("C2", policy={"tool_whitelist": ["fx_api", "calculator"]}),
        ]
        results = [
            _FakeResult("C1", trace=_make_trace(
                [StepType.ACT, StepType.ACT],
                tool_calls_map={
                    0: [ToolCallRecord(tool_name="weather_api", tool_args={}, tool_call_id="1")],
                    1: [ToolCallRecord(tool_name="calculator", tool_args={}, tool_call_id="2")],
                }
            )),
            _FakeResult("C2", trace=_make_trace(
                [StepType.ACT], tool_calls_map={0: [
                    ToolCallRecord(tool_name="fx_api", tool_args={}, tool_call_id="3")
                ]}
            )),
        ]

        flag_rate, total_v, tasks_v = compute_policy_violations(results, tasks)
        assert abs(flag_rate - 0.5) < 1e-9
        assert total_v == 1
        assert tasks_v == 1

    def test_no_policy_tasks(self):
        """No tasks with policy → flag_rate = 0.0"""
        tasks = [_FakeTask("A1", policy=None)]
        results = [_FakeResult("A1")]
        flag_rate, _, _ = compute_policy_violations(results, tasks)
        assert flag_rate == 0.0

    def test_task_failed_no_trace(self):
        """Task failed (no trace) → not counted as violation."""
        tasks = [_FakeTask("C1", policy={"tool_whitelist": ["weather_api"]})]
        results = [_FakeResult("C1", trace=None, success=False)]
        flag_rate, total_v, tasks_v = compute_policy_violations(results, tasks)
        assert flag_rate == 0.0
        assert total_v == 0
