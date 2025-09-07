"""New LangGraph Agent.

This module defines a custom graph.
"""

from agent.graph import graph
from agent.graph_simple import graph_simple
from agent.graph_manual import graph_manual

__all__ = [
    "graph",
    "graph_simple",
    "graph_manual",
]
