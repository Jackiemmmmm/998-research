"""Baseline Pattern - Raw LLM without any agentic framework.

Control group for evaluating the added value of agentic design patterns.
Single LLM call with no tools, no reasoning chain, no iteration.
"""

from typing import Annotated

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.llm_config import get_llm


class BaselineState(TypedDict):
    """State for baseline (raw LLM) pattern."""

    messages: Annotated[list, add_messages]
    evaluation_mode: bool


llm = get_llm()


def llm_node(state: BaselineState):
    """Single LLM call — no tools, no reasoning, no iteration."""
    user_input = state["messages"][-1].content if state["messages"] else ""
    evaluation_mode = state.get("evaluation_mode", False)

    if evaluation_mode:
        prompt = (
            f"{user_input}\n\n"
            "Respond with ONLY the direct answer. "
            "No explanations, no prefixes, no extra text."
        )
    else:
        prompt = user_input

    response = llm.invoke([{"role": "user", "content": prompt}])

    # Preserve token metadata from LLM response
    ai_msg = AIMessage(content=response.content.strip())
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        ai_msg.usage_metadata = response.usage_metadata
    if hasattr(response, "response_metadata") and response.response_metadata:
        ai_msg.response_metadata = response.response_metadata

    return {
        "messages": state["messages"] + [ai_msg],
        "evaluation_mode": evaluation_mode,
    }


# Build graph: START → llm_node → END
builder = StateGraph(BaselineState)
builder.add_node("llm", llm_node)
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

graph_pattern_baseline = builder.compile()
