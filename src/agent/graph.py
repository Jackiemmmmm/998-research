"""Agent graph configuration module.

This module sets up the default graph for the agent.
Available patterns:
  - graph_pattern_react / enhanced_graph_pattern_react (ReAct)
  - graph_pattern_reflex (Reflex)
  - graph_pattern_sequential (Sequential / CoT)
  - graph_pattern_tree_of_thoughts (Tree of Thoughts / ToT)
"""

from dotenv import load_dotenv

from agent.pattern_tree_of_thoughts import graph_pattern_tree_of_thoughts

load_dotenv()

graph = graph_pattern_tree_of_thoughts
