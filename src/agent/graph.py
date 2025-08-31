"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

from typing import Any, Dict, TypedDict

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.prebuilt import create_react_agent


class CalcState(TypedDict):
    x: int


def addition(state: CalcState) -> CalcState:
    print(f"[addition]: {state}")
    return CalcState(x=state["x"] + 1)


def subtraction(state: CalcState) -> CalcState:
    print(f"[subtraction]: {state}")
    return CalcState(x=state["x"] - 1)


# Define the graph
graph = (
    StateGraph(
        CalcState,
    )
    .add_node("addition", addition)
    .add_node("subtraction", subtraction)
    .add_edge("__start__", "addition")
    .add_edge("addition", "subtraction")
    .add_edge("subtraction", "__end__")
    .compile(name="New Graph")
)
