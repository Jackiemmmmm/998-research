from langgraph.prebuilt import create_react_agent
from src.tool import tools
from src.llm_config import get_llm

graph_simple = create_react_agent(model=get_llm(), tools=tools)
