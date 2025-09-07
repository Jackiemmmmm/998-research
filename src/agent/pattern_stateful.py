"""
State-based Pattern Demo - 状态控制模式
适用场景：复杂业务逻辑，需要智能决策
特点：基于状态的动态路由和错误恢复，最佳容错性
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode
from src.tool import tools


class StatefulState(TypedDict):
    messages: Annotated[list, add_messages]
    complexity: str  # "simple", "medium", "complex"
    retry_count: int
    max_retries: int
    decision_history: list
    context: dict
    current_strategy: str


# 初始化模型
llm = init_chat_model("google_genai:gemini-2.0-flash")


def analyzer_node(state: StatefulState):
    """分析节点：评估任务复杂度和选择策略"""
    analyzer_llm = llm.bind_tools([])

    query = state["messages"][-1].content if state["messages"] else "No query"

    # 构建正确的消息格式
    analysis_messages = [
        {
            "role": "user",
            "content": f"""You are an intelligent task analyzer in a state-based pattern system.

Query to analyze: {query}

Your task: Analyze the complexity and determine the best processing strategy.

Complexity Levels:
- SIMPLE: Direct questions, basic information requests
- MEDIUM: Multi-step reasoning, comparisons, analysis
- COMPLEX: Multi-domain knowledge, planning, complex reasoning

Strategy Options:
- DIRECT: Fast processing for simple tasks
- STRUCTURED: Step-by-step for medium tasks  
- ADAPTIVE: Dynamic approach for complex tasks

Please respond in this format:
COMPLEXITY: [SIMPLE/MEDIUM/COMPLEX]
STRATEGY: [DIRECT/STRUCTURED/ADAPTIVE]
REASONING: [Your reasoning for this classification]
""",
        }
    ]

    response = analyzer_llm.invoke(analysis_messages)
    analysis_text = response.content

    # 解析复杂度
    complexity = "medium"  # 默认值
    strategy = "structured"  # 默认值

    if "COMPLEXITY: SIMPLE" in analysis_text.upper():
        complexity = "simple"
        strategy = "direct"
    elif "COMPLEXITY: COMPLEX" in analysis_text.upper():
        complexity = "complex"
        strategy = "adaptive"

    decision_history = [f"Analysis: {complexity} complexity, {strategy} strategy"]

    return {
        "messages": state["messages"]
        + [{"role": "assistant", "content": f"🔍 Analysis: {analysis_text}"}],
        "complexity": complexity,
        "retry_count": 0,
        "max_retries": 3,
        "decision_history": decision_history,
        "context": {"analysis": analysis_text},
        "current_strategy": strategy,
    }


def simple_processor_node(state: StatefulState):
    """简单处理器：快速直接处理"""
    processor_llm = llm.bind_tools(tools)

    # 构建正确的消息格式，包含对话历史
    processor_messages = state["messages"] + [
        {
            "role": "user",
            "content": f"""You are a SIMPLE processor in a state-based system.

Strategy: Direct and efficient processing
Complexity Level: {state.get('complexity', 'simple')}

Guidelines:
- Provide quick, direct answers
- Use tools only when absolutely necessary
- Focus on efficiency and speed
- Keep responses concise

Please process this query efficiently.
""",
        }
    ]

    response = processor_llm.invoke(processor_messages)

    decision_history = state.get("decision_history", [])
    decision_history.append("Processing: Used simple processor")

    return {
        "messages": state["messages"]
        + [
            {
                "role": "assistant",
                "content": f"⚡ Simple Processing: {response.content}",
            }
        ],
        "complexity": state.get("complexity"),
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "decision_history": decision_history,
        "context": state.get("context", {}),
        "current_strategy": state.get("current_strategy"),
    }


def structured_processor_node(state: StatefulState):
    """结构化处理器：系统化处理"""
    processor_llm = llm.bind_tools(tools)

    # 构建正确的消息格式，包含对话历史
    processor_messages = state["messages"] + [
        {
            "role": "user",
            "content": f"""You are a STRUCTURED processor in a state-based system.

Strategy: Systematic step-by-step processing
Complexity Level: {state.get('complexity', 'medium')}
Previous Analysis: {state.get('context', {}).get('analysis', 'No prior analysis')}

Guidelines:
- Break down the task into logical steps
- Use tools systematically when needed
- Provide comprehensive but organized responses
- Show your reasoning process

Please process this query systematically.
""",
        }
    ]

    response = processor_llm.invoke(processor_messages)

    decision_history = state.get("decision_history", [])
    decision_history.append("Processing: Used structured processor")

    return {
        "messages": state["messages"]
        + [
            {
                "role": "assistant",
                "content": f"🏗️ Structured Processing: {response.content}",
            }
        ],
        "complexity": state.get("complexity"),
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "decision_history": decision_history,
        "context": state.get("context", {}),
        "current_strategy": state.get("current_strategy"),
    }


def adaptive_processor_node(state: StatefulState):
    """自适应处理器：动态调整处理方式"""
    processor_llm = llm.bind_tools(tools)

    # 构建正确的消息格式，包含对话历史
    processor_messages = state["messages"] + [
        {
            "role": "user",
            "content": f"""You are an ADAPTIVE processor in a state-based system.

Strategy: Dynamic and flexible processing
Complexity Level: {state.get('complexity', 'complex')}
Previous Decisions: {'; '.join(state.get('decision_history', []))}
Current Context: {state.get('context', {})}

Guidelines:
- Adapt your approach based on the specific needs
- Use advanced reasoning and multiple tools if needed
- Consider edge cases and alternative solutions
- Provide comprehensive and nuanced responses

Please process this complex query with full adaptive capabilities.
""",
        }
    ]

    response = processor_llm.invoke(processor_messages)

    decision_history = state.get("decision_history", [])
    decision_history.append("Processing: Used adaptive processor")

    # 检查是否可能需要重试
    needs_retry = (
        "error" in response.content.lower() or "failed" in response.content.lower()
    )
    retry_count = state.get("retry_count", 0)

    if needs_retry and retry_count < state.get("max_retries", 3):
        decision_history.append(
            f"Retry {retry_count + 1}: Detected potential issue, preparing retry"
        )
        return {
            "messages": state["messages"],  # 保持原始消息
            "complexity": state.get("complexity"),
            "retry_count": retry_count + 1,
            "max_retries": state.get("max_retries", 3),
            "decision_history": decision_history,
            "context": state.get("context", {}),
            "current_strategy": "adaptive_retry",
        }

    return {
        "messages": state["messages"]
        + [
            {
                "role": "assistant",
                "content": f"🧠 Adaptive Processing: {response.content}",
            }
        ],
        "complexity": state.get("complexity"),
        "retry_count": retry_count,
        "max_retries": state.get("max_retries", 3),
        "decision_history": decision_history,
        "context": state.get("context", {}),
        "current_strategy": state.get("current_strategy"),
    }


def validator_node(state: StatefulState):
    """验证节点：最终验证和总结"""
    validator_llm = llm.bind_tools([])

    # 构建正确的消息格式
    validation_messages = [
        {
            "role": "user",
            "content": f"""You are a VALIDATOR in a state-based system.

Processing Summary:
- Complexity: {state.get('complexity', 'unknown')}
- Strategy Used: {state.get('current_strategy', 'unknown')}
- Retry Count: {state.get('retry_count', 0)}
- Decision History: {'; '.join(state.get('decision_history', []))}

Your task: Validate the processing results and provide final summary.

Guidelines:
- Assess the quality and completeness of the response
- Highlight the decision-making process that led to this result
- Demonstrate the benefits of the state-based approach
- Provide final polished response

Please validate and summarize the results.
""",
        }
    ]

    response = validator_llm.invoke(validation_messages)

    decision_history = state.get("decision_history", [])
    decision_history.append("Validation: Completed final validation")

    return {
        "messages": state["messages"]
        + [
            {
                "role": "assistant",
                "content": f"✅ Validation Complete: {response.content}",
            }
        ],
        "complexity": state.get("complexity"),
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "decision_history": decision_history,
        "context": state.get("context", {}),
        "current_strategy": state.get("current_strategy"),
    }


def handle_tools(state: StatefulState):
    """处理工具调用"""
    tool_node = ToolNode(tools=tools)
    result = tool_node.invoke(state)

    decision_history = state.get("decision_history", [])
    decision_history.append("Tools: Executed tool calls")

    return {**result, "decision_history": decision_history}


# 路由函数
def route_after_analysis(
    state: StatefulState,
) -> Literal["simple_processor", "structured_processor", "adaptive_processor"]:
    """分析后的路由决策"""
    complexity = state.get("complexity", "medium")
    strategy = state.get("current_strategy", "structured")

    if complexity == "simple" or strategy == "direct":
        return "simple_processor"
    elif complexity == "complex" or strategy == "adaptive":
        return "adaptive_processor"
    else:
        return "structured_processor"


def route_after_processing(
    state: StatefulState,
) -> Literal[
    "simple_processor",
    "structured_processor",
    "adaptive_processor",
    "tools",
    "validator",
]:
    """处理后的路由决策"""
    # 检查工具调用
    last_message = state["messages"][-1] if state["messages"] else None
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # 检查重试 - 但要防止无限循环
    strategy = state.get("current_strategy", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # 只有在重试次数未达上限且明确标记需要重试时才重试
    if strategy == "adaptive_retry" and retry_count < max_retries:
        return "adaptive_processor"

    # 否则都进入验证阶段
    return "validator"


def route_after_tools(state: StatefulState) -> Literal["validator"]:
    """工具调用后路由到验证"""
    return "validator"


# 构建状态图
builder = StateGraph(StatefulState)

# 添加所有节点
builder.add_node("analyzer", analyzer_node)
builder.add_node("simple_processor", simple_processor_node)
builder.add_node("structured_processor", structured_processor_node)
builder.add_node("adaptive_processor", adaptive_processor_node)
builder.add_node("validator", validator_node)
builder.add_node("tools", handle_tools)

# 添加边和路由
builder.add_edge(START, "analyzer")
builder.add_conditional_edges("analyzer", route_after_analysis)
builder.add_conditional_edges("simple_processor", route_after_processing)
builder.add_conditional_edges("structured_processor", route_after_processing)
builder.add_conditional_edges("adaptive_processor", route_after_processing)
builder.add_conditional_edges("tools", route_after_tools)
builder.add_edge("validator", END)

# 编译图，设置递归限制
graph_pattern_stateful = builder.compile(
    checkpointer=None,
    # 设置递归限制，防止无限循环
)
