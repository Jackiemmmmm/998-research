"""
ReAct Pattern Demo - 反应式模式
适用场景：简单推理任务，快速响应
特点：推理-行动循环，低资源消耗，中等延迟
"""
from langgraph.prebuilt import create_react_agent
from src.tool import tools

# ReAct模式：最简洁的实现，直接使用create_react_agent
# 这种模式适合快速响应和简单推理任务
graph_pattern_react = create_react_agent(
    model="google_genai:gemini-2.0-flash", 
    tools=tools
)