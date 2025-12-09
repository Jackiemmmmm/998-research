"""Hybrid multi-agent implementation.

This module implements a hybrid multi-agent system combining custom StateGraph
with prebuilt ReAct agents for research and analysis tasks.
"""

from typing import Annotated, Literal

from dotenv import load_dotenv
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict

from src.llm_config import get_llm
from src.tool import tools

load_dotenv()


class HybridState(TypedDict):
    """State for hybrid multi-agent workflow."""

    messages: Annotated[list, add_messages]
    stage: str

# 创建专门的agent
research_agent = create_react_agent(
    model=get_llm(),
    tools=tools,
    system_message="You are a research specialist. Gather comprehensive information."
)

analysis_agent = create_react_agent(
    model=get_llm(), 
    tools=[],  # 分析agent不需要工具，只分析已有信息
    system_message="You are an analysis specialist. Analyze and synthesize information."
)

# 包装函数，使agent适配StateGraph
def research_node(state: HybridState):
    """研究节点 - 使用create_react_agent."""
    result = research_agent.invoke(state)
    return {
        "messages": result["messages"],
        "stage": "research_complete"
    }

def analysis_node(state: HybridState):
    """分析节点 - 使用create_react_agent."""
    result = analysis_agent.invoke(state)
    return {
        "messages": result["messages"],
        "stage": "analysis_complete"
    }

# 路由函数
def route_next(state: HybridState) -> Literal["analysis", "__end__"]:
    """决定下一步路由."""
    if state.get("stage") == "research_complete":
        return "analysis"
    else:
        return "__end__"

# 构建混合图
builder = StateGraph(HybridState)

# 添加节点
builder.add_node("research", research_node)
builder.add_node("analysis", analysis_node)

# 添加边
builder.add_edge(START, "research")
builder.add_conditional_edges("research", route_next)

# 编译
graph_multi_hybrid = builder.compile()