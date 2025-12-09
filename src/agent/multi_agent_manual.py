"""Manual multi-agent implementation.

This module provides a manually constructed multi-agent system with
research and analysis agents using StateGraph.
"""

from typing import Annotated, Literal

from dotenv import load_dotenv
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.llm_config import get_llm
from src.tool import tools

load_dotenv()


class MultiAgentState(TypedDict):
    """State for multi-agent workflow with research and analysis phases."""

    messages: Annotated[list, add_messages]
    current_agent: str
    research_complete: bool
    analysis_complete: bool

# 初始化模型
llm = get_llm()
llm_with_tools = llm.bind_tools(tools)

# 研究agent节点
def research_agent(state: MultiAgentState):
    """专门负责研究和信息收集的agent."""
    system_msg = {"role": "system", "content": "You are a research agent. Focus on gathering comprehensive information using available tools."}
    messages = [system_msg] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "current_agent": "research",
        "research_complete": not (hasattr(response, 'tool_calls') and response.tool_calls)
    }

# 分析agent节点
def analysis_agent(state: MultiAgentState):
    """专门负责分析和总结的agent."""
    system_msg = {"role": "system", "content": "You are an analysis agent. Analyze the research findings and provide insights."}
    messages = [system_msg] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "current_agent": "analysis", 
        "analysis_complete": True
    }

# 决策函数：决定下一步去哪里
def decide_next_step(state: MultiAgentState) -> Literal["research", "analysis", "tools", "__end__"]:
    """决定工作流的下一步."""
    last_message = state["messages"][-1]
    
    # 如果有tool调用，去执行工具
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # 根据当前agent和完成状态决定下一步
    if state.get("current_agent") == "research" and state.get("research_complete"):
        return "analysis"
    elif state.get("analysis_complete"):
        return "__end__"
    else:
        return "research"

# 构建图
builder = StateGraph(MultiAgentState)

# 添加节点
builder.add_node("research", research_agent)
builder.add_node("analysis", analysis_agent)
builder.add_node("tools", ToolNode(tools=tools))

# 添加条件边
builder.add_conditional_edges("research", decide_next_step)
builder.add_conditional_edges("analysis", decide_next_step)

# 工具执行后的路由
def after_tools(state: MultiAgentState) -> Literal["research", "analysis"]:
    """工具执行后返回到相应的agent."""
    return state.get("current_agent", "research")

builder.add_conditional_edges("tools", after_tools)

# 设置入口
builder.add_edge(START, "research")

# 编译图
graph_multi_manual = builder.compile()