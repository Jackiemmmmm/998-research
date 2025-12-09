"""Agent graph configuration module.

This module sets up the default graph for the agent.
"""

from dotenv import load_dotenv

from agent.pattern_tree_of_thoughts import graph_pattern_tree_of_thoughts

load_dotenv()

# {"messages": [{"role": "user", "content": "What date today? and What's weather in Wollongong today?"}]}

# graph = graph_manual
# graph = graph_simple

# graph = enhanced_graph_pattern_react  # ReAct模式：推理-行动-观察循环，适合复杂推理任务
# graph = graph_pattern_react        # Basic ReAct模式：基础版本
# graph = graph_pattern_sequential   # Chain of Thought模式：规划-执行-审查流水线
# graph = graph_pattern_reflex       # Reflex Agent模式：基于规则的快速响应
graph = graph_pattern_tree_of_thoughts  # Tree of Thoughts模式：并行探索多个解决路径
