from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from src.tool import tools
from src.llm_config import get_llm


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm = get_llm()
llm_with_tools = llm.bind_tools(tools)
graph_builder = StateGraph(State)


def chatbot(state: State):
    response = llm_with_tools.invoke(state["messages"])
    print(f"LLM response type: {type(response)}")
    print(f"Has tool_calls: {hasattr(response, 'tool_calls') and response.tool_calls}")
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
