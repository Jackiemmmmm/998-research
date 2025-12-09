"""Simple multi-agent workflow implementation.

This module creates a simple multi-agent workflow using prebuilt ReAct agents
for research and analysis tasks.
"""

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent

from src.llm_config import get_llm
from src.tool import tools

load_dotenv()

# 创建多个专门的agent
research_agent = create_react_agent(
    model=get_llm(), 
    tools=tools,
    system_message="You are a research agent. Focus on gathering information and facts."
)

analysis_agent = create_react_agent(
    model=get_llm(),
    tools=tools,
    system_message="You are an analysis agent. Focus on analyzing data and drawing conclusions."
)

# 协调器函数
def multi_agent_workflow(user_input):
    """协调多个agent的工作流程."""
    # 第一步：研究agent收集信息
    research_result = research_agent.invoke({
        "messages": [{"role": "user", "content": f"Research: {user_input}"}]
    })
    
    # 第二步：分析agent处理研究结果
    research_content = research_result["messages"][-1].content
    analysis_result = analysis_agent.invoke({
        "messages": [{"role": "user", "content": f"Analyze this research: {research_content}"}]
    })
    
    return analysis_result

# 导出主要工作流
graph_multi_simple = multi_agent_workflow