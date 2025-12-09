"""ReAct Pattern Demo - 反应式模式 (Enhanced).

适用场景：复杂推理任务，多步骤问题解决，工具调用序列
特点：推理-行动-观察循环，动态任务分解，可解释推理过程.

Based on IBM's ReAct agent best practices:
- Combines reasoning and acting in iterative loops
- Decomposes complex tasks into manageable subtasks
- Uses external tools and APIs for grounding
- Provides explainable reasoning through verbalized thoughts
- Includes termination conditions and iteration limits
"""
from langgraph.prebuilt import create_react_agent

from src.llm_config import get_llm
from src.tool import tools

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
   - IMPORTANT: For simple reasoning tasks (math, logic, comparisons), you can solve them directly without tools

2. **ACTION**: Take a specific action using available tools (only when needed)
   - Choose the most appropriate tool for your current need
   - Provide clear, specific parameters for tool calls
   - Only take one action at a time
   - Skip this step if you can answer using reasoning alone

3. **OBSERVATION**: Analyze the results of your action
   - Interpret the information you received
   - Determine if you've made progress toward your goal
   - Decide whether you need to take additional actions
   - Update your understanding based on new information

4. **REPEAT**: Continue the Thought-Action-Observation cycle until you have enough information to provide a final answer

CRITICAL OUTPUT FORMATTING RULES (MUST FOLLOW EXACTLY):
- When the user asks for "Output the number only", output JUST the number, nothing else
- When the user asks for "Output X only" or "Return X only", output ONLY that exact value with ZERO additional text
- For JSON requests: Return ONLY valid JSON, no explanations, no markdown code blocks
- For number-only requests: Return ONLY the number (e.g., "408" NOT "17 * 24 = 408")
- For single-word requests: Return ONLY that word (e.g., "Paris" NOT "The capital is Paris")
- DO NOT include calculations, explanations, or reasoning in your final output
- DO NOT add phrases like "Based on...", "The answer is...", "According to...", "Here is..."
- DO NOT use markdown formatting (```), bullet points, or any decorations
- Your FINAL MESSAGE must contain ONLY the requested output, nothing more
- Read the task instructions carefully and follow output format requirements EXACTLY

REASONING GUIDELINES:
- For simple arithmetic (like 17 × 24): Calculate directly, don't use tools
- For logic puzzles (if A>B and B>C, then A>C): Reason through them directly
- For reading comprehension: Extract answer from given text directly
- Only use tools when you need external information (weather, prices, search, etc.)

Available tools: {tool_names}

Remember: Quality reasoning leads to better actions, and clean outputs that follow instructions exactly.
"""

# Configuration for the enhanced ReAct agent
REACT_CONFIG = {
    "max_execution_time": 300,  # 5 minutes timeout
    "max_iterations": 20,      # Maximum reasoning-action cycles
    "recursion_limit": 50,     # LangGraph recursion limit
}

# Create a wrapper function to add system prompt to the ReAct agent
def create_enhanced_react_agent_with_prompt(model, tools, system_prompt=None):
    """Create a ReAct agent with enhanced system prompt.

    Uses the `prompt` parameter of create_react_agent to inject system message.
    This is the correct way per LangGraph API.
    """
    if system_prompt:
        # Use the prompt parameter to inject system message
        return create_react_agent(
            model=model,
            tools=tools,
            prompt=system_prompt  # Can be SystemMessage or string
        )
    else:
        return create_react_agent(model=model, tools=tools)

# Create the basic ReAct agent (maintains compatibility)
# 使用配置的 LLM
graph_pattern_react = create_react_agent(
    model=get_llm(),
    tools=tools
)

# Create the enhanced ReAct agent with system prompt
enhanced_graph_pattern_react = create_enhanced_react_agent_with_prompt(
    model=get_llm(),
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
