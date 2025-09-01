from dotenv import load_dotenv

from agent.graph_simple import graph_simple
from agent.graph_manual import graph_manual

load_dotenv()

# {"messages": [{"role": "user", "content": "What date today? and What's weather in Wollongong today?"}]}

# graph = graph_manual
graph = graph_simple
