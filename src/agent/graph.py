from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain.chat_models import init_chat_model

from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv

from src.tool import tools


load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm = init_chat_model("google_genai:gemini-2.0-flash")

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
graph = graph_builder.compile()
