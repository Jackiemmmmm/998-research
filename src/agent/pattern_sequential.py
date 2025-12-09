"""Sequential Pattern Demo - 顺序处理模式.

适用场景：多步骤标准化流程
特点：规划→执行→审查的流水线，高延迟但结果可靠.
"""

from typing import Annotated

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.llm_config import get_llm
from src.tool import tools


class SequentialState(TypedDict):
    """State for sequential pattern with planning, execution, and review stages."""

    messages: Annotated[list, add_messages]
    stage: str
    plan: str
    execution_result: str
    evaluation_mode: bool  # If True, output clean results without verbose formatting


# 初始化模型 - 使用配置的 LLM
llm = get_llm()


# 规划节点
def planning_node(state: SequentialState):
    """第一阶段：任务规划."""
    planning_llm = llm.bind_tools([])  # 规划阶段不使用工具

    # 获取用户的原始查询
    user_query = state["messages"][-1].content if state["messages"] else "No query"

    # 构建正确的消息格式
    planning_messages = [
        {
            "role": "user",
            "content": f"""You are in the PLANNING stage of a sequential processing pattern.

Original query: {user_query}

Your task: Create a detailed step-by-step plan to address this query.

Characteristics of Sequential Pattern:
- Break down complex tasks into clear sequential steps
- Plan before executing
- Ensure comprehensive coverage

Please provide a numbered plan (1, 2, 3, etc.) for handling this query.
Format: "PLAN: [your detailed plan here]"
""",
        }
    ]

    response = planning_llm.invoke(planning_messages)
    plan = response.content

    return {
        "messages": state["messages"]
        + [AIMessage(content=f"📋 Planning Stage: {plan}")],
        "stage": "execution",
        "plan": plan,
        "execution_result": "",
        "evaluation_mode": state.get("evaluation_mode", False),
    }


# 执行节点
def execution_node(state: SequentialState):
    """第二阶段：计划执行."""
    # 绑定工具，让execution阶段可以使用工具
    execution_llm = llm.bind_tools(tools)

    # 获取原始用户查询
    original_query = (
        state["messages"][0].content if state["messages"] else "No original query"
    )

    # 构建执行消息 - 让LLM完成所有必要的工具调用
    execution_messages = [
        {
            "role": "user", 
            "content": f"""You are executing a plan to answer this question: "{original_query}"

Plan to follow: {state.get('plan', 'No plan available')}

Execute this plan completely. Use tools when needed for information you cannot provide directly. Once you have all the information needed to answer the user's question comprehensively, provide a complete response without using any more tools.

Your goal is to provide a final, complete answer to the user's question.""",
        }
    ]

    try:
        response = execution_llm.invoke(execution_messages)

        # 直接返回LLM响应，让tools_condition决定路由
        execution_content = (
            response.content.strip() if response.content else "No response generated"
        )

        return {
            "messages": state["messages"] + [response],
            "stage": "review",
            "plan": state.get("plan", ""),
            "execution_result": execution_content,
            "evaluation_mode": state.get("evaluation_mode", False),
        }
    except Exception as e:
        error_message = f"Execution failed with error: {str(e)}"
        return {
            "messages": state["messages"]
            + [AIMessage(content=f"⚡ Execution Stage: {error_message}")],
            "stage": "review",
            "plan": state.get("plan", ""),
            "execution_result": error_message,
            "evaluation_mode": state.get("evaluation_mode", False),
        }


# 审查节点
def review_node(state: SequentialState):
    """第三阶段：结果审查."""
    review_llm = llm.bind_tools([])  # 审查阶段不使用工具

    # 获取原始用户查询
    original_query = (
        state["messages"][0].content if state["messages"] else "No original query"
    )

    # Check if in evaluation mode
    evaluation_mode = state.get("evaluation_mode", False)

    # Adjust prompt based on evaluation mode
    if evaluation_mode:
        # Evaluation mode: output only the concise answer
        review_prompt = f"""You are in the REVIEW stage of a sequential processing pattern.

Original User Query: {original_query}
Plan Created: {state.get('plan', 'No plan')}
Execution Result: {state.get('execution_result', 'No execution result')}

Your task: Provide ONLY the direct answer to the user's query. Be extremely concise.

IMPORTANT:
- Output ONLY the answer itself, nothing more
- For calculations: output only the number (e.g., "408", not "The result is 408")
- For facts: output only the fact (e.g., "Paris", not "The capital is Paris")
- For dates: output only the date in requested format
- For JSON: output only the JSON object
- NO explanations, NO prefixes, NO formatting

Provide only the answer:"""
    else:
        # Demo mode: comprehensive user-friendly response
        review_prompt = f"""You are in the REVIEW stage of a sequential processing pattern.

Original User Query: {original_query}
Plan Created: {state.get('plan', 'No plan')}
Execution Result: {state.get('execution_result', 'No execution result')}

Your task: Provide a final, comprehensive answer to the user's original query.

Guidelines:
- Synthesize the planning and execution results into a cohesive response
- Address the user's original question directly and completely
- Include key insights from the systematic analysis
- Present the information in a clear, user-friendly format
- Don't mention internal stages - just provide the final answer

Please provide the final answer that directly addresses the user's query."""

    # 构建正确的消息格式
    review_messages = [{"role": "user", "content": review_prompt}]

    response = review_llm.invoke(review_messages)

    # 提供最终的整合答案，使用AIMessage确保正确显示
    final_message = AIMessage(content=response.content)

    return {
        "messages": state["messages"] + [final_message],
        "stage": "completed",
        "plan": state.get("plan", ""),
        "execution_result": state.get("execution_result", ""),
        "evaluation_mode": state.get("evaluation_mode", False),
    }


# 路由函数已简化，直接在图构建中使用边连接

# 构建图
builder = StateGraph(SequentialState)

# 添加节点
builder.add_node("planning", planning_node)
builder.add_node("execution", execution_node)
builder.add_node("review", review_node)

# 不需要单独的tools节点，execution自己处理工具调用

# 配置边 - 交给LLM自行判断
builder.add_edge(START, "planning")
builder.add_edge("planning", "execution")
# 最简单的配置：execution完成后直接到review
builder.add_edge("execution", "review")
builder.add_edge("review", END)

# 编译图
graph_pattern_sequential = builder.compile()
