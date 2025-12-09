"""Manual graph implementation for LangGraph agent.

This module provides a manually constructed StateGraph for the chatbot agent.
"""

from typing import Annotated

from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from src.llm_config import get_llm
from src.tool import tools


class State(TypedDict):
    """State for the chatbot containing messages."""

    messages: Annotated[list, add_messages]


llm = get_llm()
llm_with_tools = llm.bind_tools(tools)
graph_builder = StateGraph(State)


def chatbot(state: State):
    """Process user message and generate response."""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

graph_manual = graph_builder.compile()
