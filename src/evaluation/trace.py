"""Unified Telemetry Layer - Trace extraction for agentic design patterns.

Provides standardized think-act-observe (TAO) telemetry schema used for
multi-dimensional evaluation. Uses post-hoc message parsing strategy:
extracts structured traces from graph.invoke() responses without modifying
any pattern's internal logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StepType(Enum):
    """Step type in the think-act-observe cycle."""

    INPUT = "input"
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    OUTPUT = "output"


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""

    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: str
    result: str = ""
    success: bool = True


@dataclass
class StepRecord:
    """Single step record in the agent trace."""

    step_index: int
    step_type: StepType
    content: str

    # Tool calls made in this step (for ACT steps)
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tokens_estimated: bool = False

    # Message metadata
    message_type: str = ""  # "human", "ai", "tool", "synthetic"
    stage_label: str = ""  # Pattern-specific annotation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_index": self.step_index,
            "step_type": self.step_type.value,
            "content": self.content[:500] if self.content else "",
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "tool_args": tc.tool_args,
                    "tool_call_id": tc.tool_call_id,
                    "success": tc.success,
                }
                for tc in self.tool_calls
            ],
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tokens_estimated": self.tokens_estimated,
            "message_type": self.message_type,
            "stage_label": self.stage_label,
        }


@dataclass
class AgentTrace:
    """Complete trace for a single task execution."""

    pattern_name: str
    task_id: str
    steps: List[StepRecord] = field(default_factory=list)

    # Aggregated step counts
    total_think_steps: int = 0
    total_act_steps: int = 0
    total_observe_steps: int = 0
    total_tool_calls: int = 0
    tao_cycles: int = 0

    # Aggregated token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    any_tokens_estimated: bool = False

    def compute_aggregates(self) -> None:
        """Recompute all aggregate fields from steps."""
        self.total_think_steps = sum(
            1 for s in self.steps if s.step_type == StepType.THINK
        )
        self.total_act_steps = sum(
            1 for s in self.steps if s.step_type == StepType.ACT
        )
        self.total_observe_steps = sum(
            1 for s in self.steps if s.step_type == StepType.OBSERVE
        )
        self.total_tool_calls = sum(len(s.tool_calls) for s in self.steps)

        # TAO cycles: count sequences of THINK followed by ACT followed by OBSERVE
        self.tao_cycles = self._count_tao_cycles()

        # Token aggregation
        self.total_input_tokens = sum(s.input_tokens for s in self.steps)
        self.total_output_tokens = sum(s.output_tokens for s in self.steps)
        self.total_tokens = sum(s.total_tokens for s in self.steps)
        self.any_tokens_estimated = any(s.tokens_estimated for s in self.steps)

    def _count_tao_cycles(self) -> int:
        """Count complete Think-Act-Observe cycles."""
        cycles = 0
        types = [s.step_type for s in self.steps]
        i = 0
        while i < len(types) - 2:
            if (
                types[i] == StepType.THINK
                and types[i + 1] == StepType.ACT
                and types[i + 2] == StepType.OBSERVE
            ):
                cycles += 1
                i += 3
            else:
                i += 1
        return cycles

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace (without raw messages)."""
        return {
            "pattern_name": self.pattern_name,
            "task_id": self.task_id,
            "steps": [s.to_dict() for s in self.steps],
            "total_think_steps": self.total_think_steps,
            "total_act_steps": self.total_act_steps,
            "total_observe_steps": self.total_observe_steps,
            "total_tool_calls": self.total_tool_calls,
            "tao_cycles": self.tao_cycles,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "any_tokens_estimated": self.any_tokens_estimated,
            "total_steps": len(self.steps),
        }


class TraceExtractor:
    """Unified trace extraction from pattern responses.

    Extracts structured AgentTrace from graph.invoke() responses
    by dispatching to pattern-specific extractors.
    """

    # Pattern name normalization mapping
    _PATTERN_MAP = {
        "react": "_extract_react",
        "reflex": "_extract_reflex",
        "sequential": "_extract_sequential",
        "cot": "_extract_sequential",
        "tot": "_extract_tot",
        "tree_of_thoughts": "_extract_tot",
    }

    @classmethod
    def extract(
        cls,
        response: Any,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Extract an AgentTrace from a pattern response.

        Args:
            response: The raw response from graph.invoke()
            pattern_name: Name of the pattern (e.g., "ReAct", "CoT")
            task_id: The task identifier

        Returns:
            AgentTrace with all steps and aggregates computed
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)

        if not isinstance(response, dict):
            return trace

        # Normalize pattern name for dispatch
        key = pattern_name.lower().replace(" ", "_").replace("-", "_")

        # Find extractor method
        method_name = cls._PATTERN_MAP.get(key, "_extract_generic")
        extractor = getattr(cls, method_name)

        trace = extractor(response, pattern_name, task_id)
        trace.compute_aggregates()
        return trace

    @classmethod
    def _get_messages(cls, response: Dict) -> list:
        """Extract messages list from response."""
        if "values" in response:
            return response["values"].get("messages", [])
        return response.get("messages", [])

    @classmethod
    def _get_content(cls, msg: Any) -> str:
        """Get content from a message (object or dict)."""
        if hasattr(msg, "content"):
            return msg.content or ""
        if isinstance(msg, dict):
            return msg.get("content", "")
        return str(msg)

    @classmethod
    def _get_message_type(cls, msg: Any) -> str:
        """Determine message type string."""
        type_name = type(msg).__name__.lower()
        if "human" in type_name:
            return "human"
        if "tool" in type_name:
            return "tool"
        if "ai" in type_name:
            return "ai"
        if isinstance(msg, dict):
            role = msg.get("role", msg.get("type", ""))
            if role in ("user", "human"):
                return "human"
            if role in ("assistant", "ai"):
                return "ai"
            if role == "tool":
                return "tool"
        return "unknown"

    @classmethod
    def _extract_tokens(cls, msg: Any) -> tuple:
        """Extract token counts from a message.

        Returns:
            (input_tokens, output_tokens, total_tokens, estimated)
        """
        # Try usage_metadata first (LLM provider data)
        usage = getattr(msg, "usage_metadata", None)
        if usage and isinstance(usage, dict):
            input_t = usage.get("input_tokens", 0)
            output_t = usage.get("output_tokens", 0)
            total_t = usage.get("total_tokens", input_t + output_t)
            if input_t > 0 or output_t > 0:
                return (input_t, output_t, total_t, False)

        # Try response_metadata
        resp_meta = getattr(msg, "response_metadata", None)
        if resp_meta and isinstance(resp_meta, dict):
            token_usage = resp_meta.get("token_usage", resp_meta.get("usage", {}))
            if isinstance(token_usage, dict):
                input_t = token_usage.get("prompt_tokens", token_usage.get("input_tokens", 0))
                output_t = token_usage.get("completion_tokens", token_usage.get("output_tokens", 0))
                if input_t > 0 or output_t > 0:
                    total_t = token_usage.get("total_tokens", input_t + output_t)
                    return (input_t, output_t, total_t, False)

        # Fallback: estimate from content length
        content = cls._get_content(msg)
        estimated_tokens = len(content) // 4 if content else 0
        msg_type = cls._get_message_type(msg)
        if msg_type == "human":
            return (estimated_tokens, 0, estimated_tokens, True)
        else:
            return (0, estimated_tokens, estimated_tokens, True)

    @classmethod
    def _has_tool_calls(cls, msg: Any) -> bool:
        """Check if an AI message has tool calls."""
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            return len(tool_calls) > 0
        if isinstance(msg, dict):
            return bool(msg.get("tool_calls"))
        return False

    @classmethod
    def _get_tool_calls(cls, msg: Any) -> List[ToolCallRecord]:
        """Extract tool call records from an AI message."""
        records = []
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls and isinstance(msg, dict):
            tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            return records

        for tc in tool_calls:
            if isinstance(tc, dict):
                records.append(ToolCallRecord(
                    tool_name=tc.get("name", ""),
                    tool_args=tc.get("args", {}),
                    tool_call_id=tc.get("id", ""),
                ))
            else:
                records.append(ToolCallRecord(
                    tool_name=getattr(tc, "name", ""),
                    tool_args=getattr(tc, "args", {}),
                    tool_call_id=getattr(tc, "id", ""),
                ))
        return records

    @classmethod
    def _get_tool_call_id(cls, msg: Any) -> str:
        """Get tool_call_id from a ToolMessage."""
        if hasattr(msg, "tool_call_id"):
            return msg.tool_call_id or ""
        if isinstance(msg, dict):
            return msg.get("tool_call_id", "")
        return ""

    @classmethod
    def _get_tool_name(cls, msg: Any) -> str:
        """Get tool name from a ToolMessage."""
        if hasattr(msg, "name"):
            return msg.name or ""
        if isinstance(msg, dict):
            return msg.get("name", "")
        return ""

    @classmethod
    def _pair_tool_results(
        cls,
        act_steps: List[StepRecord],
        observe_steps: List[StepRecord],
    ) -> None:
        """Pair ACT tool_call_ids with OBSERVE results.

        Matches OBSERVE steps to their corresponding ToolCallRecords
        in ACT steps via tool_call_id, filling in the result field.
        """
        # Build lookup: tool_call_id -> ToolCallRecord
        tc_lookup: Dict[str, ToolCallRecord] = {}
        for step in act_steps:
            for tc in step.tool_calls:
                if tc.tool_call_id:
                    tc_lookup[tc.tool_call_id] = tc

        # Match OBSERVE steps to tool call records
        for step in observe_steps:
            # tool_call_id stored in stage_label for OBSERVE steps
            tc_id = step.stage_label
            if tc_id and tc_id in tc_lookup:
                tc_lookup[tc_id].result = step.content

    # ---- Pattern-specific extractors ----

    @classmethod
    def _extract_react(
        cls,
        response: Dict,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Extract trace from ReAct pattern response.

        ReAct flow: HumanMessage -> AIMessage(content+tool_calls) -> ToolMessage -> ... -> AIMessage(final)

        - AIMessage with content + tool_calls -> THINK (reasoning) + ACT (tool calls)
        - ToolMessage -> OBSERVE
        - Final AIMessage without tool_calls -> OUTPUT
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)
        messages = cls._get_messages(response)

        step_idx = 0
        act_steps = []
        observe_steps = []

        for msg in messages:
            msg_type = cls._get_message_type(msg)
            content = cls._get_content(msg)
            input_t, output_t, total_t, estimated = cls._extract_tokens(msg)

            if msg_type == "human":
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.INPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="human",
                    stage_label="react_input",
                ))
                step_idx += 1

            elif msg_type == "ai":
                if cls._has_tool_calls(msg):
                    # THINK step: the reasoning content
                    if content:
                        trace.steps.append(StepRecord(
                            step_index=step_idx,
                            step_type=StepType.THINK,
                            content=content,
                            input_tokens=input_t,
                            output_tokens=output_t,
                            total_tokens=total_t,
                            tokens_estimated=estimated,
                            message_type="ai",
                            stage_label="react_reasoning",
                        ))
                        step_idx += 1
                        # Reset tokens for ACT step (avoid double counting)
                        input_t, output_t, total_t = 0, 0, 0

                    # ACT step: the tool calls
                    tool_records = cls._get_tool_calls(msg)
                    act_step = StepRecord(
                        step_index=step_idx,
                        step_type=StepType.ACT,
                        content=", ".join(tc.tool_name for tc in tool_records),
                        tool_calls=tool_records,
                        input_tokens=input_t,
                        output_tokens=output_t,
                        total_tokens=total_t,
                        tokens_estimated=estimated,
                        message_type="ai",
                        stage_label="react_action",
                    )
                    trace.steps.append(act_step)
                    act_steps.append(act_step)
                    step_idx += 1
                else:
                    # Final AI message without tool calls -> OUTPUT
                    trace.steps.append(StepRecord(
                        step_index=step_idx,
                        step_type=StepType.OUTPUT,
                        content=content,
                        input_tokens=input_t,
                        output_tokens=output_t,
                        total_tokens=total_t,
                        tokens_estimated=estimated,
                        message_type="ai",
                        stage_label="react_output",
                    ))
                    step_idx += 1

            elif msg_type == "tool":
                tool_call_id = cls._get_tool_call_id(msg)
                observe_step = StepRecord(
                    step_index=step_idx,
                    step_type=StepType.OBSERVE,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="tool",
                    stage_label=tool_call_id,  # Store tool_call_id for pairing
                )
                trace.steps.append(observe_step)
                observe_steps.append(observe_step)
                step_idx += 1

        # Pair ACT tool calls with OBSERVE results
        cls._pair_tool_results(act_steps, observe_steps)

        return trace

    @classmethod
    def _extract_reflex(
        cls,
        response: Dict,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Extract trace from Reflex pattern response.

        Reflex flow: single-pass rule matching.
        State contains matched_rule and action_taken.
        Synthesizes a THINK step from rule/action info.
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)
        messages = cls._get_messages(response)

        step_idx = 0

        # Extract state-level info
        matched_rule = response.get("matched_rule", "")
        action_taken = response.get("action_taken", "")

        for msg in messages:
            msg_type = cls._get_message_type(msg)
            content = cls._get_content(msg)
            input_t, output_t, total_t, estimated = cls._extract_tokens(msg)

            if msg_type == "human":
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.INPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="human",
                    stage_label="reflex_input",
                ))
                step_idx += 1

        # Synthesize THINK step from matched_rule + action_taken
        if matched_rule or action_taken:
            think_content = f"Rule: {matched_rule}"
            if action_taken:
                think_content += f" | Action: {action_taken}"
            trace.steps.append(StepRecord(
                step_index=step_idx,
                step_type=StepType.THINK,
                content=think_content,
                tokens_estimated=True,
                message_type="synthetic",
                stage_label="reflex_rule_match",
            ))
            step_idx += 1

        # Final AI message -> OUTPUT
        for msg in messages:
            msg_type = cls._get_message_type(msg)
            if msg_type == "ai":
                content = cls._get_content(msg)
                input_t, output_t, total_t, estimated = cls._extract_tokens(msg)
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.OUTPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="ai",
                    stage_label="reflex_output",
                ))
                step_idx += 1

        return trace

    @classmethod
    def _extract_sequential(
        cls,
        response: Dict,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Extract trace from Sequential/CoT pattern response.

        Sequential flow: planning -> execution -> review
        AI messages are annotated by stage:
          - 1st AI message -> THINK (cot_planning)
          - Middle AI messages -> ACT/THINK (cot_execution)
          - Last AI message -> OUTPUT (cot_review)
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)
        messages = cls._get_messages(response)

        step_idx = 0

        # Separate messages by type
        ai_messages = []
        for msg in messages:
            msg_type = cls._get_message_type(msg)
            content = cls._get_content(msg)
            input_t, output_t, total_t, estimated = cls._extract_tokens(msg)

            if msg_type == "human":
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.INPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="human",
                    stage_label="cot_input",
                ))
                step_idx += 1
            elif msg_type == "ai":
                ai_messages.append((msg, content, input_t, output_t, total_t, estimated))
            elif msg_type == "tool":
                # Tool messages in sequential -> OBSERVE
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.OBSERVE,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="tool",
                    stage_label="cot_tool_result",
                ))
                step_idx += 1

        # Annotate AI messages by position
        for i, (msg, content, input_t, output_t, total_t, estimated) in enumerate(ai_messages):
            if i == 0:
                # First AI message = planning stage
                step_type = StepType.THINK
                stage_label = "cot_planning"
            elif i == len(ai_messages) - 1 and len(ai_messages) > 1:
                # Last AI message = review/output stage
                step_type = StepType.OUTPUT
                stage_label = "cot_review"
            else:
                # Middle AI messages = execution stage
                if cls._has_tool_calls(msg):
                    step_type = StepType.ACT
                    stage_label = "cot_execution_act"
                else:
                    step_type = StepType.THINK
                    stage_label = "cot_execution"

            tool_records = cls._get_tool_calls(msg) if cls._has_tool_calls(msg) else []

            trace.steps.append(StepRecord(
                step_index=step_idx,
                step_type=step_type,
                content=content,
                tool_calls=tool_records,
                input_tokens=input_t,
                output_tokens=output_t,
                total_tokens=total_t,
                tokens_estimated=estimated,
                message_type="ai",
                stage_label=stage_label,
            ))
            step_idx += 1

        return trace

    @classmethod
    def _extract_tot(
        cls,
        response: Dict,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Extract trace from Tree of Thoughts pattern response.

        ToT flow: thought generation -> evaluation -> search/prune -> synthesis
        Messages contain INPUT + OUTPUT; thought_tree state rebuilds THINK steps.
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)
        messages = cls._get_messages(response)

        step_idx = 0

        # Process messages for INPUT and OUTPUT
        for msg in messages:
            msg_type = cls._get_message_type(msg)
            content = cls._get_content(msg)
            input_t, output_t, total_t, estimated = cls._extract_tokens(msg)

            if msg_type == "human":
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.INPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="human",
                    stage_label="tot_input",
                ))
                step_idx += 1

        # Reconstruct THINK steps from thought_tree
        thought_tree = response.get("thought_tree", [])
        for thought in thought_tree:
            if isinstance(thought, dict):
                thought_content = thought.get("content", "")
                score = thought.get("score", 0.0)
                depth = thought.get("depth", 0)
                reasoning = thought.get("reasoning", "")
                path = thought.get("path", [])

                content = f"[depth={depth}, score={score:.2f}] {thought_content}"
                if reasoning:
                    content += f" | Reasoning: {reasoning}"
                if path:
                    content += f" | Path: {' -> '.join(str(p) for p in path)}"

                # Estimate tokens from content (synthetic step)
                est_tokens = len(content) // 4

                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.THINK,
                    content=content,
                    output_tokens=est_tokens,
                    total_tokens=est_tokens,
                    tokens_estimated=True,
                    message_type="synthetic",
                    stage_label=f"tot_thought_d{depth}",
                ))
                step_idx += 1

        # Final AI message -> OUTPUT
        for msg in messages:
            msg_type = cls._get_message_type(msg)
            if msg_type == "ai":
                content = cls._get_content(msg)
                input_t, output_t, total_t, estimated = cls._extract_tokens(msg)
                trace.steps.append(StepRecord(
                    step_index=step_idx,
                    step_type=StepType.OUTPUT,
                    content=content,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    total_tokens=total_t,
                    tokens_estimated=estimated,
                    message_type="ai",
                    stage_label="tot_output",
                ))
                step_idx += 1

        return trace

    @classmethod
    def _extract_generic(
        cls,
        response: Dict,
        pattern_name: str,
        task_id: str,
    ) -> AgentTrace:
        """Generic fallback extractor for unknown patterns.

        Classifies messages as INPUT (human), THINK/ACT (ai), OBSERVE (tool).
        """
        trace = AgentTrace(pattern_name=pattern_name, task_id=task_id)
        messages = cls._get_messages(response)

        step_idx = 0

        for i, msg in enumerate(messages):
            msg_type = cls._get_message_type(msg)
            content = cls._get_content(msg)
            input_t, output_t, total_t, estimated = cls._extract_tokens(msg)

            if msg_type == "human":
                step_type = StepType.INPUT
                stage_label = "generic_input"
            elif msg_type == "tool":
                step_type = StepType.OBSERVE
                stage_label = "generic_observe"
            elif msg_type == "ai":
                if cls._has_tool_calls(msg):
                    step_type = StepType.ACT
                    stage_label = "generic_act"
                elif i == len(messages) - 1:
                    step_type = StepType.OUTPUT
                    stage_label = "generic_output"
                else:
                    step_type = StepType.THINK
                    stage_label = "generic_think"
            else:
                step_type = StepType.THINK
                stage_label = "generic_unknown"

            tool_records = (
                cls._get_tool_calls(msg)
                if msg_type == "ai" and cls._has_tool_calls(msg)
                else []
            )

            trace.steps.append(StepRecord(
                step_index=step_idx,
                step_type=step_type,
                content=content,
                tool_calls=tool_records,
                input_tokens=input_t,
                output_tokens=output_t,
                total_tokens=total_t,
                tokens_estimated=estimated,
                message_type=msg_type,
                stage_label=stage_label,
            ))
            step_idx += 1

        return trace
