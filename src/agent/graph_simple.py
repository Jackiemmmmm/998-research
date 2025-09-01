from langgraph.prebuilt import create_react_agent
from src.tool import tools

graph_simple = create_react_agent(model="google_genai:gemini-2.0-flash", tools=tools)
