"""Unit tests for the unified telemetry trace extraction module."""

import pytest

from src.evaluation.trace import (
    AgentTrace,
    StepRecord,
    StepType,
    ToolCallRecord,
    TraceExtractor,
)


# ---- Mock message classes mimicking LangChain message types ----


class MockHumanMessage:
    """Mock LangChain HumanMessage."""

    def __init__(self, content: str, usage_metadata=None):
        self.content = content
        self.type = "human"
        self.usage_metadata = usage_metadata


class MockAIMessage:
    """Mock LangChain AIMessage."""

    def __init__(self, content: str, tool_calls=None, usage_metadata=None, response_metadata=None):
        self.content = content
        self.type = "ai"
        self.tool_calls = tool_calls or []
        self.usage_metadata = usage_metadata
        self.response_metadata = response_metadata


class MockToolMessage:
    """Mock LangChain ToolMessage."""

    def __init__(self, content: str, tool_call_id: str = "", name: str = ""):
        self.content = content
        self.type = "tool"
        self.tool_call_id = tool_call_id
        self.name = name
        self.usage_metadata = None


# ---- ReAct pattern tests ----


class TestExtractReact:
    """Tests for ReAct pattern trace extraction."""

    def test_basic_react_flow(self):
        """Test HumanMessage -> AIMessage(content+tool_calls) -> ToolMessage -> AIMessage(final)."""
        response = {
            "messages": [
                MockHumanMessage("What is the weather in Paris?"),
                MockAIMessage(
                    content="I need to check the weather. Let me use the weather tool.",
                    tool_calls=[
                        {"name": "get_weather", "args": {"city": "Paris"}, "id": "call_001"}
                    ],
                ),
                MockToolMessage(
                    content="Paris: 22°C, sunny",
                    tool_call_id="call_001",
                    name="get_weather",
                ),
                MockAIMessage(content="The weather in Paris is 22°C and sunny."),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_001")

        assert trace.pattern_name == "react"
        assert trace.task_id == "task_001"

        # Check step types: INPUT, THINK, ACT, OBSERVE, OUTPUT
        step_types = [s.step_type for s in trace.steps]
        assert step_types == [
            StepType.INPUT,
            StepType.THINK,
            StepType.ACT,
            StepType.OBSERVE,
            StepType.OUTPUT,
        ]

        # Check THINK step content
        think_step = [s for s in trace.steps if s.step_type == StepType.THINK][0]
        assert "weather tool" in think_step.content

        # Check ACT step has tool calls
        act_step = [s for s in trace.steps if s.step_type == StepType.ACT][0]
        assert len(act_step.tool_calls) == 1
        assert act_step.tool_calls[0].tool_name == "get_weather"
        assert act_step.tool_calls[0].tool_args == {"city": "Paris"}

        # Check aggregates
        assert trace.total_think_steps == 1
        assert trace.total_act_steps == 1
        assert trace.total_observe_steps == 1
        assert trace.total_tool_calls == 1
        assert trace.tao_cycles == 1

    def test_react_multiple_tool_calls(self):
        """Test ReAct with multiple tool call iterations."""
        response = {
            "messages": [
                MockHumanMessage("Compare weather in Paris and London"),
                MockAIMessage(
                    content="Let me check Paris first.",
                    tool_calls=[
                        {"name": "get_weather", "args": {"city": "Paris"}, "id": "call_001"}
                    ],
                ),
                MockToolMessage(content="Paris: 22°C", tool_call_id="call_001"),
                MockAIMessage(
                    content="Now let me check London.",
                    tool_calls=[
                        {"name": "get_weather", "args": {"city": "London"}, "id": "call_002"}
                    ],
                ),
                MockToolMessage(content="London: 15°C", tool_call_id="call_002"),
                MockAIMessage(content="Paris is 22°C and London is 15°C."),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_002")

        assert trace.total_think_steps == 2
        assert trace.total_act_steps == 2
        assert trace.total_observe_steps == 2
        assert trace.total_tool_calls == 2
        assert trace.tao_cycles == 2

    def test_react_no_tool_calls(self):
        """Test ReAct with direct answer (no tool usage)."""
        response = {
            "messages": [
                MockHumanMessage("What is 2+2?"),
                MockAIMessage(content="4"),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_003")

        step_types = [s.step_type for s in trace.steps]
        assert step_types == [StepType.INPUT, StepType.OUTPUT]
        assert trace.total_tool_calls == 0
        assert trace.tao_cycles == 0

    def test_react_ai_no_content_with_tool_calls(self):
        """Test ReAct where AI message has tool_calls but empty content."""
        response = {
            "messages": [
                MockHumanMessage("Get weather"),
                MockAIMessage(
                    content="",
                    tool_calls=[
                        {"name": "get_weather", "args": {"city": "Paris"}, "id": "call_001"}
                    ],
                ),
                MockToolMessage(content="Paris: 22°C", tool_call_id="call_001"),
                MockAIMessage(content="22°C in Paris"),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_004")

        # No THINK step since content was empty
        step_types = [s.step_type for s in trace.steps]
        assert StepType.THINK not in step_types
        assert trace.total_act_steps == 1
        assert trace.total_observe_steps == 1


# ---- Reflex pattern tests ----


class TestExtractReflex:
    """Tests for Reflex pattern trace extraction."""

    def test_basic_reflex_flow(self):
        """Test reflex with matched_rule and action_taken in state."""
        response = {
            "messages": [
                MockHumanMessage("What is the weather in Paris?"),
                MockAIMessage(content="The weather in Paris is sunny, 22°C."),
            ],
            "matched_rule": "weather_query",
            "action_taken": "Reflex executed: weather lookup | Tools: get_weather",
        }

        trace = TraceExtractor.extract(response, "reflex", "task_010")

        assert trace.pattern_name == "reflex"

        # Should have INPUT, THINK (synthetic), OUTPUT
        step_types = [s.step_type for s in trace.steps]
        assert StepType.INPUT in step_types
        assert StepType.THINK in step_types
        assert StepType.OUTPUT in step_types

        # Check synthetic THINK step
        think_step = [s for s in trace.steps if s.step_type == StepType.THINK][0]
        assert "weather_query" in think_step.content
        assert think_step.message_type == "synthetic"
        assert think_step.stage_label == "reflex_rule_match"

    def test_reflex_no_rule_match(self):
        """Test reflex without matched_rule (fallback)."""
        response = {
            "messages": [
                MockHumanMessage("Hello"),
                MockAIMessage(content="Hi there!"),
            ],
        }

        trace = TraceExtractor.extract(response, "reflex", "task_011")

        # No THINK step without matched_rule
        step_types = [s.step_type for s in trace.steps]
        assert StepType.THINK not in step_types
        assert StepType.INPUT in step_types
        assert StepType.OUTPUT in step_types


# ---- Sequential/CoT pattern tests ----


class TestExtractSequential:
    """Tests for Sequential (CoT) pattern trace extraction."""

    def test_basic_sequential_flow(self):
        """Test 3-stage flow: planning -> execution -> review."""
        response = {
            "messages": [
                MockHumanMessage("Calculate 15% tip on $85.50"),
                MockAIMessage(content="Plan: 1. Calculate 15% of 85.50"),
                MockAIMessage(content="Executing: 85.50 * 0.15 = 12.825"),
                MockAIMessage(content="$12.83"),
            ],
            "stage": "completed",
            "plan": "1. Calculate 15% of 85.50",
            "execution_result": "85.50 * 0.15 = 12.825",
        }

        trace = TraceExtractor.extract(response, "sequential", "task_020")

        step_types = [s.step_type for s in trace.steps]

        # INPUT, THINK (planning), THINK (execution middle), OUTPUT (review)
        assert step_types[0] == StepType.INPUT
        assert step_types[1] == StepType.THINK  # planning
        assert step_types[-1] == StepType.OUTPUT  # review

        # Check stage labels
        planning_step = trace.steps[1]
        assert planning_step.stage_label == "cot_planning"

        review_step = trace.steps[-1]
        assert review_step.stage_label == "cot_review"

    def test_sequential_single_ai_message(self):
        """Test sequential with only one AI message."""
        response = {
            "messages": [
                MockHumanMessage("What is 2+2?"),
                MockAIMessage(content="4"),
            ],
        }

        trace = TraceExtractor.extract(response, "cot", "task_021")

        step_types = [s.step_type for s in trace.steps]
        # Single AI message = planning (THINK)
        assert step_types == [StepType.INPUT, StepType.THINK]


# ---- ToT pattern tests ----


class TestExtractToT:
    """Tests for Tree of Thoughts pattern trace extraction."""

    def test_basic_tot_flow(self):
        """Test ToT with thought_tree in state."""
        response = {
            "messages": [
                MockHumanMessage("What is the best approach to sort a linked list?"),
                MockAIMessage(content="Merge sort is the best approach for sorting linked lists."),
            ],
            "thought_tree": [
                {
                    "content": "Use merge sort for linked list",
                    "path": ["divide", "merge"],
                    "depth": 1,
                    "score": 0.9,
                    "reasoning": "O(n log n) and works well with linked list structure",
                },
                {
                    "content": "Use bubble sort",
                    "path": ["compare", "swap"],
                    "depth": 1,
                    "score": 0.3,
                    "reasoning": "Simple but O(n^2)",
                },
                {
                    "content": "Recursive merge sort implementation",
                    "path": ["divide", "merge", "recurse"],
                    "depth": 2,
                    "score": 0.85,
                    "reasoning": "Natural recursive structure",
                },
            ],
            "current_depth": 2,
            "best_thoughts": [
                {"content": "Use merge sort for linked list", "score": 0.9, "depth": 1},
            ],
        }

        trace = TraceExtractor.extract(response, "tot", "task_030")

        assert trace.pattern_name == "tot"

        # Should have INPUT, 3 THINK steps (from thought_tree), and OUTPUT
        step_types = [s.step_type for s in trace.steps]
        assert step_types.count(StepType.INPUT) == 1
        assert step_types.count(StepType.THINK) == 3
        assert step_types.count(StepType.OUTPUT) == 1

        # THINK steps should be marked as synthetic/estimated
        think_steps = [s for s in trace.steps if s.step_type == StepType.THINK]
        for ts in think_steps:
            assert ts.tokens_estimated is True
            assert ts.message_type == "synthetic"

        # Check depth annotation
        assert "d1" in think_steps[0].stage_label
        assert "d2" in think_steps[2].stage_label

    def test_tot_empty_thought_tree(self):
        """Test ToT with empty thought_tree."""
        response = {
            "messages": [
                MockHumanMessage("Simple question"),
                MockAIMessage(content="Simple answer"),
            ],
            "thought_tree": [],
        }

        trace = TraceExtractor.extract(response, "tree_of_thoughts", "task_031")

        step_types = [s.step_type for s in trace.steps]
        assert step_types == [StepType.INPUT, StepType.OUTPUT]
        assert trace.total_think_steps == 0


# ---- Token extraction tests ----


class TestTokenExtraction:
    """Tests for token extraction with usage_metadata priority and fallback."""

    def test_usage_metadata_priority(self):
        """Test that usage_metadata is used when available."""
        msg = MockAIMessage(
            content="Hello world",
            usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )

        input_t, output_t, total_t, estimated = TraceExtractor._extract_tokens(msg)

        assert input_t == 10
        assert output_t == 5
        assert total_t == 15
        assert estimated is False

    def test_response_metadata_fallback(self):
        """Test response_metadata token extraction when usage_metadata is absent."""
        msg = MockAIMessage(
            content="Hello world",
            response_metadata={
                "token_usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 8,
                    "total_tokens": 28,
                }
            },
        )

        input_t, output_t, total_t, estimated = TraceExtractor._extract_tokens(msg)

        assert input_t == 20
        assert output_t == 8
        assert total_t == 28
        assert estimated is False

    def test_estimated_fallback(self):
        """Test fallback to len//4 estimation when no metadata available."""
        msg = MockAIMessage(content="Hello world! This is a test message.")

        input_t, output_t, total_t, estimated = TraceExtractor._extract_tokens(msg)

        expected = len("Hello world! This is a test message.") // 4
        assert output_t == expected  # AI messages -> output_tokens
        assert input_t == 0
        assert total_t == expected
        assert estimated is True

    def test_human_message_estimated(self):
        """Test that human messages estimate as input_tokens."""
        msg = MockHumanMessage(content="What is the weather?")

        input_t, output_t, total_t, estimated = TraceExtractor._extract_tokens(msg)

        expected = len("What is the weather?") // 4
        assert input_t == expected
        assert output_t == 0
        assert estimated is True

    def test_aggregated_tokens_in_trace(self):
        """Test that trace correctly aggregates tokens from steps."""
        response = {
            "messages": [
                MockHumanMessage("Test", usage_metadata={"input_tokens": 5, "output_tokens": 0, "total_tokens": 5}),
                MockAIMessage(
                    content="Response",
                    usage_metadata={"input_tokens": 5, "output_tokens": 10, "total_tokens": 15},
                ),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_tok")

        assert trace.total_input_tokens == 10  # 5 + 5
        assert trace.total_output_tokens == 10  # 0 + 10
        assert trace.total_tokens == 20  # 5 + 15
        assert trace.any_tokens_estimated is False

    def test_mixed_estimated_and_real(self):
        """Test any_tokens_estimated when some are estimated and some are real."""
        response = {
            "messages": [
                MockHumanMessage("Test"),  # No metadata -> estimated
                MockAIMessage(
                    content="Response",
                    usage_metadata={"input_tokens": 5, "output_tokens": 10, "total_tokens": 15},
                ),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_mix")
        assert trace.any_tokens_estimated is True


# ---- Tool pairing tests ----


class TestToolPairing:
    """Tests for ACT -> OBSERVE tool_call_id pairing."""

    def test_tool_pairing_basic(self):
        """Test that tool results are paired with their ACT steps."""
        response = {
            "messages": [
                MockHumanMessage("Test"),
                MockAIMessage(
                    content="Let me search.",
                    tool_calls=[
                        {"name": "search", "args": {"q": "test"}, "id": "call_100"}
                    ],
                ),
                MockToolMessage(
                    content="Search result: found 5 items",
                    tool_call_id="call_100",
                    name="search",
                ),
                MockAIMessage(content="Found 5 items."),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_pair")

        # Find the ACT step and check its tool call has result
        act_step = [s for s in trace.steps if s.step_type == StepType.ACT][0]
        assert len(act_step.tool_calls) == 1
        assert act_step.tool_calls[0].result == "Search result: found 5 items"
        assert act_step.tool_calls[0].tool_call_id == "call_100"

    def test_tool_pairing_multiple(self):
        """Test pairing with multiple tool calls in sequence."""
        response = {
            "messages": [
                MockHumanMessage("Compare weather"),
                MockAIMessage(
                    content="Checking both cities.",
                    tool_calls=[
                        {"name": "get_weather", "args": {"city": "Paris"}, "id": "call_a"},
                        {"name": "get_weather", "args": {"city": "London"}, "id": "call_b"},
                    ],
                ),
                MockToolMessage(content="Paris: 22°C", tool_call_id="call_a"),
                MockToolMessage(content="London: 15°C", tool_call_id="call_b"),
                MockAIMessage(content="Paris is warmer."),
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_pair2")

        act_step = [s for s in trace.steps if s.step_type == StepType.ACT][0]
        assert len(act_step.tool_calls) == 2

        tc_a = next(tc for tc in act_step.tool_calls if tc.tool_call_id == "call_a")
        tc_b = next(tc for tc in act_step.tool_calls if tc.tool_call_id == "call_b")

        assert tc_a.result == "Paris: 22°C"
        assert tc_b.result == "London: 15°C"


# ---- Data structure tests ----


class TestDataStructures:
    """Tests for data structure methods."""

    def test_agent_trace_to_dict(self):
        """Test AgentTrace serialization."""
        trace = AgentTrace(pattern_name="react", task_id="t1")
        trace.steps.append(StepRecord(
            step_index=0, step_type=StepType.INPUT, content="Hello",
            message_type="human",
        ))
        trace.steps.append(StepRecord(
            step_index=1, step_type=StepType.OUTPUT, content="World",
            message_type="ai",
        ))
        trace.compute_aggregates()

        d = trace.to_dict()
        assert d["pattern_name"] == "react"
        assert d["task_id"] == "t1"
        assert d["total_steps"] == 2
        assert len(d["steps"]) == 2
        assert d["steps"][0]["step_type"] == "input"
        assert d["steps"][1]["step_type"] == "output"

    def test_tao_cycle_counting(self):
        """Test TAO cycle detection."""
        trace = AgentTrace(pattern_name="react", task_id="t2")
        # Build T-A-O-T-A-O sequence
        types = [StepType.THINK, StepType.ACT, StepType.OBSERVE,
                 StepType.THINK, StepType.ACT, StepType.OBSERVE]
        for i, st in enumerate(types):
            trace.steps.append(StepRecord(step_index=i, step_type=st, content=""))
        trace.compute_aggregates()

        assert trace.tao_cycles == 2

    def test_tao_cycle_incomplete(self):
        """Test that incomplete TAO sequences are not counted."""
        trace = AgentTrace(pattern_name="react", task_id="t3")
        # T-A only (no O)
        trace.steps.append(StepRecord(step_index=0, step_type=StepType.THINK, content=""))
        trace.steps.append(StepRecord(step_index=1, step_type=StepType.ACT, content=""))
        trace.compute_aggregates()

        assert trace.tao_cycles == 0

    def test_step_record_to_dict(self):
        """Test StepRecord serialization."""
        step = StepRecord(
            step_index=0,
            step_type=StepType.ACT,
            content="search",
            tool_calls=[
                ToolCallRecord(
                    tool_name="search",
                    tool_args={"q": "test"},
                    tool_call_id="c1",
                    result="found",
                    success=True,
                )
            ],
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            tokens_estimated=False,
            message_type="ai",
            stage_label="react_action",
        )

        d = step.to_dict()
        assert d["step_type"] == "act"
        assert len(d["tool_calls"]) == 1
        assert d["tool_calls"][0]["tool_name"] == "search"
        assert d["input_tokens"] == 10

    def test_tool_call_record_defaults(self):
        """Test ToolCallRecord default values."""
        tc = ToolCallRecord(tool_name="test", tool_args={}, tool_call_id="c1")
        assert tc.result == ""
        assert tc.success is True


# ---- Generic extractor tests ----


class TestExtractGeneric:
    """Tests for the generic fallback extractor."""

    def test_unknown_pattern(self):
        """Test that unknown patterns use generic extractor."""
        response = {
            "messages": [
                MockHumanMessage("Question"),
                MockAIMessage(content="Thinking about it..."),
                MockAIMessage(content="Answer"),
            ]
        }

        trace = TraceExtractor.extract(response, "unknown_pattern", "task_gen")

        step_types = [s.step_type for s in trace.steps]
        assert step_types == [StepType.INPUT, StepType.THINK, StepType.OUTPUT]

    def test_empty_response(self):
        """Test extraction from empty response."""
        trace = TraceExtractor.extract({}, "react", "task_empty")
        assert len(trace.steps) == 0
        assert trace.total_tokens == 0

    def test_non_dict_response(self):
        """Test extraction from non-dict response."""
        trace = TraceExtractor.extract("raw string", "react", "task_str")
        assert len(trace.steps) == 0


# ---- Edge case tests ----


class TestEdgeCases:
    """Edge case tests."""

    def test_values_wrapper(self):
        """Test response wrapped in 'values' key."""
        response = {
            "values": {
                "messages": [
                    MockHumanMessage("Test"),
                    MockAIMessage(content="Response"),
                ]
            }
        }

        trace = TraceExtractor.extract(response, "react", "task_vals")
        assert len(trace.steps) == 2

    def test_dict_messages(self):
        """Test response with dict messages instead of objects."""
        response = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        }

        trace = TraceExtractor.extract(response, "react", "task_dict")
        assert len(trace.steps) == 2
        assert trace.steps[0].step_type == StepType.INPUT
        assert trace.steps[1].step_type == StepType.OUTPUT
