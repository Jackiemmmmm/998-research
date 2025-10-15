"""
Reflex Agent Pattern Demo - 反射代理模式
适用场景：简单快速响应，基于规则的决策
特点：直接的if-then规则匹配，立即响应，极低延迟

Based on plan.md requirements:
- Receives input
- Matches input to predefined action using simple if-then rules
- Executes action immediately
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage
# 不需要 ToolNode 和 tools_condition - Reflex Agent 直接调用工具
from src.tool import tools
from src.llm_config import get_llm
import re


class ReflexState(TypedDict):
    messages: Annotated[list, add_messages]
    matched_rule: str
    action_taken: str


# 初始化模型 - 使用配置的 LLM
llm = get_llm()

# 定义反射规则集 - 简单的if-then规则
REFLEX_RULES = [
    # 天气查询规则
    {
        "pattern": r"weather|天气|temperature|温度|forecast|预报",
        "action": "weather_query",
        "response": "I'll check the weather for you using the weather tool.",
        "tool_required": True,
        "priority": 1
    },

    # 搜索查询规则
    {
        "pattern": r"search|find|look up|查找|搜索|google",
        "action": "search_query",
        "response": "I'll search for that information using the search tool.",
        "tool_required": True,
        "priority": 2
    },

    # 计算规则
    {
        "pattern": r"calculate|compute|math|数学|计算|\d+[\+\-\*/]\d+",
        "action": "calculation",
        "response": "I'll perform that calculation for you.",
        "tool_required": False,
        "priority": 1
    },

    # 时间查询规则
    {
        "pattern": r"time|clock|date|时间|日期|几点|what time",
        "action": "time_query",
        "response": "I'll get the current time for you.",
        "tool_required": False,
        "priority": 1
    },

    # 问候规则
    {
        "pattern": r"hello|hi|hey|greet|你好|嗨|问候",
        "action": "greeting",
        "response": "Hello! How can I help you today?",
        "tool_required": False,
        "priority": 3
    },

    # 帮助规则
    {
        "pattern": r"help|assist|support|帮助|协助",
        "action": "help_request",
        "response": "I'm here to help! You can ask me about weather, search for information, do calculations, get time, or just chat.",
        "tool_required": False,
        "priority": 2
    },

    # 默认规则（最低优先级）
    {
        "pattern": r".*",
        "action": "general_response",
        "response": "Let me help you with that query.",
        "tool_required": True,
        "priority": 10
    }
]


def rule_matcher_node(state: ReflexState):
    """规则匹配节点：分析输入，匹配多个规则并立即执行对应动作"""

    # 获取用户输入
    user_input = state["messages"][-1].content if state["messages"] else ""
    user_input_lower = user_input.lower()

    # 查找所有匹配的规则（按优先级排序）- 支持复合查询，但排除默认规则以避免重复
    matched_rules = []
    for rule in sorted(REFLEX_RULES, key=lambda x: x["priority"]):
        if rule["action"] != "general_response" and re.search(rule["pattern"], user_input_lower, re.IGNORECASE):
            matched_rules.append(rule)

    # 如果没有匹配到任何具体规则，使用默认规则
    if not matched_rules:
        matched_rules = [REFLEX_RULES[-1]]  # 默认规则

    messages = state["messages"]
    response_parts = []
    tools_used = []
    actions_taken = []

    # Reflex Agent: 根据匹配的规则执行对应动作
    from src.tool import tools  # 移到循环外部，确保所有分支都能访问

    for rule in matched_rules:
        action = rule["action"]
        actions_taken.append(action)

        if action == "weather_query":
            # 天气查询 - 使用搜索工具
            search_tool = next(tool for tool in tools if tool.name == "tavily_search_results_json")
            try:
                result = search_tool.invoke({"query": f"weather {user_input}"})
                response_parts.append(f"🌤️ Weather Information:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception as e:
                response_parts.append(f"🌤️ Weather lookup failed: {str(e)}")
                tools_used.append("tavily_search_results_json (failed)")

        elif action == "time_query":
            # 时间查询 - 使用日期工具
            date_tool = next((tool for tool in tools if "get_current_date" in tool.name), None)
            if date_tool:
                try:
                    result = date_tool.invoke({})
                    response_parts.append(f"🕒 Current Date/Time:\n{result}")
                    tools_used.append(date_tool.name)
                except Exception as e:
                    response_parts.append(f"🕒 Date lookup failed: {str(e)}")
                    tools_used.append(f"{date_tool.name} (failed)")
            else:
                response_parts.append("🕒 Current time: Date tool not available in this demo.")
                tools_used.append("date_tool (not available)")

        elif action == "search_query":
            # 搜索查询 - 使用搜索工具
            search_tool = next(tool for tool in tools if tool.name == "tavily_search_results_json")
            try:
                result = search_tool.invoke({"query": user_input})
                response_parts.append(f"🔍 Search Results:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception as e:
                response_parts.append(f"🔍 Search failed: {str(e)}")
                tools_used.append("tavily_search_results_json (failed)")

        elif action == "calculation":
            # 计算 - 直接处理
            calc_result = _handle_calculation(user_input)
            response_parts.append(f"🧮 Calculation:\n{calc_result}")
            tools_used.append("direct_calculation")

        elif action == "greeting":
            # 问候 - 直接响应
            response_parts.append("👋 Hello! I'm a Reflex Agent designed to respond quickly to common requests. How can I help you today?")
            tools_used.append("direct_response")

        elif action == "help_request":
            # 帮助 - 直接响应
            help_text = """🤝 I'm a Reflex Agent that can quickly help with:
- Weather queries (uses search tool)
- Information searches (uses search tool)
- Simple calculations (direct processing)
- Current time (uses date tool)
- General assistance"""
            response_parts.append(help_text)
            tools_used.append("direct_response")

        elif action == "general_response":
            # 默认 - 使用搜索工具
            search_tool = next(tool for tool in tools if tool.name == "tavily_search_results_json")
            try:
                result = search_tool.invoke({"query": user_input})
                response_parts.append(f"🔧 General Help:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception as e:
                response_parts.append(f"🔧 I'll try to help: {rule.get('response', 'How can I assist you?')}")
                tools_used.append("tavily_search_results_json (failed)")

    # 构建最终响应
    tool_info = f"🔧 Tools used: {', '.join(set(tools_used))}\n\n"
    final_response = tool_info + "\n\n".join(response_parts)

    return {
        "messages": messages + [AIMessage(content=final_response)],
        "matched_rule": ", ".join(actions_taken),
        "action_taken": f"Reflex executed: {', '.join(actions_taken)} | Tools: {', '.join(set(tools_used))}"
    }



def _handle_calculation(user_input: str) -> str:
    """处理简单的数学计算"""
    import re

    # 查找简单的数学表达式
    math_pattern = r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)'
    match = re.search(math_pattern, user_input)

    if match:
        try:
            num1, operator, num2 = match.groups()
            num1, num2 = float(num1), float(num2)

            if operator == '+':
                result = num1 + num2
            elif operator == '-':
                result = num1 - num2
            elif operator == '*':
                result = num1 * num2
            elif operator == '/':
                if num2 != 0:
                    result = num1 / num2
                else:
                    return "Error: Cannot divide by zero!"
            else:
                return "Error: Unsupported operation!"

            return f"Calculation: {num1} {operator} {num2} = {result}"
        except:
            return "Error: Could not perform calculation!"

    return "I can help with simple calculations like '5 + 3' or '10 * 2'. What would you like to calculate?"



# 构建反射代理图 - 极简结构
builder = StateGraph(ReflexState)

# Reflex Agent 只需要一个节点：匹配规则并立即执行
builder.add_node("rule_matcher", rule_matcher_node)

# 极简流程：START → rule_matcher → END
builder.add_edge(START, "rule_matcher")
builder.add_edge("rule_matcher", END)

# 编译图
graph_pattern_reflex = builder.compile()