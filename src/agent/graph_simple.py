"""Simple graph using prebuilt ReAct agent.

This module creates a simple ReAct agent using LangGraph prebuilt components.
"""

from langgraph.prebuilt import create_react_agent

from src.llm_config import get_llm
from src.tool import tools

graph_simple = create_react_agent(model=get_llm(), tools=tools)
