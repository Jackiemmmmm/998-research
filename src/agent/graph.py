from dotenv import load_dotenv

from agent.graph_simple import graph_simple
from agent.graph_manual import graph_manual

from agent.pattern_react import graph_pattern_react
from agent.pattern_sequential import graph_pattern_sequential
from agent.pattern_stateful import graph_pattern_stateful

load_dotenv()

# {"messages": [{"role": "user", "content": "What date today? and What's weather in Wollongong today?"}]}

# graph = graph_manual
# graph = graph_simple

# graph = graph_pattern_react  # ReAct模式：快速响应，适合简单推理任务
graph = graph_pattern_sequential  # Sequential模式：多步流水线，适合标准化流程
# graph = graph_pattern_stateful  # State-based模式：智能决策，适合复杂业务逻辑
