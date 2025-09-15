"""
ReAct Pattern Demo - 反应式模式 (Enhanced)
适用场景：复杂推理任务，多步骤问题解决，工具调用序列
特点：推理-行动-观察循环，动态任务分解，可解释推理过程

Based on IBM's ReAct agent best practices:
- Combines reasoning and acting in iterative loops
- Decomposes complex tasks into manageable subtasks
- Uses external tools and APIs for grounding
- Provides explainable reasoning through verbalized thoughts
- Includes termination conditions and iteration limits
"""
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, BaseMessage
from src.tool import tools
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

# Enhanced ReAct agent with improved reasoning-action-observation loop
# System message that guides the agent's behavior according to ReAct principles
REACT_SYSTEM_PROMPT = """
You are an intelligent assistant that solves problems using the ReAct (Reasoning + Acting) framework.

For each task, follow this iterative process:

1. **THOUGHT**: Think step-by-step about the problem
   - Analyze what you know and what you need to find out
   - Break down complex tasks into smaller subtasks
   - Consider which tools or actions would be most helpful
   - Reason about the current state and next steps

2. **ACTION**: Take a specific action using available tools
   - Choose the most appropriate tool for your current need
   - Provide clear, specific parameters for tool calls
   - Only take one action at a time

3. **OBSERVATION**: Analyze the results of your action
   - Interpret the information you received
   - Determine if you've made progress toward your goal
   - Decide whether you need to take additional actions
   - Update your understanding based on new information

4. **REPEAT**: Continue the Thought-Action-Observation cycle until you have enough information to provide a final answer

IMPORTANT GUIDELINES:
- Always explain your reasoning before taking actions
- Use the scratchpad to keep track of your progress and findings
- Be systematic and methodical in your approach
- If you encounter errors, adapt your strategy accordingly
- Provide clear explanations of your reasoning process
- Terminate when you have sufficient information to answer the question completely

Available tools: {tool_names}

Remember: Quality reasoning leads to better actions, which produce more useful observations.
"""

# Configuration for the enhanced ReAct agent
REACT_CONFIG = {
    "max_execution_time": 300,  # 5 minutes timeout
    "max_iterations": 20,      # Maximum reasoning-action cycles
    "recursion_limit": 50,     # LangGraph recursion limit
}

# Create a wrapper function to add system prompt to the ReAct agent
def create_enhanced_react_agent_with_prompt(model, tools, system_prompt=None):
    """Create a ReAct agent with enhanced system prompt"""

    # Use the basic ReAct agent
    base_agent = create_react_agent(model=model, tools=tools)

    if system_prompt:
        # Create a wrapper that injects system message
        class AgentState(TypedDict):
            messages: Annotated[list[BaseMessage], add_messages]

        def add_system_message(state):
            messages = state["messages"]
            # Check if system message already exists
            if not messages or not isinstance(messages[0], SystemMessage):
                # Add system message at the beginning
                system_msg = SystemMessage(content=system_prompt)
                messages = [system_msg] + messages
            return {"messages": messages}

        # Create enhanced graph that adds system message before processing
        workflow = StateGraph(AgentState)
        workflow.add_node("add_system", add_system_message)
        workflow.add_node("react_agent", base_agent)
        workflow.add_edge("add_system", "react_agent")
        workflow.set_entry_point("add_system")
        workflow.set_finish_point("react_agent")

        return workflow.compile()
    else:
        return base_agent

# Create the basic ReAct agent (maintains compatibility)
graph_pattern_react = create_react_agent(
    model="google_genai:gemini-2.0-flash",
    tools=tools
)

# Create the enhanced ReAct agent with system prompt
enhanced_graph_pattern_react = create_enhanced_react_agent_with_prompt(
    model="google_genai:gemini-2.0-flash",
    tools=tools,
    system_prompt=REACT_SYSTEM_PROMPT.format(
        tool_names=", ".join([tool.name for tool in tools])
    )
)

# Export all versions for flexibility
__all__ = [
    "graph_pattern_react",              # Basic ReAct agent
    "enhanced_graph_pattern_react",     # Enhanced ReAct agent with system prompt
]
