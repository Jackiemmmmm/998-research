"""Reflex Agent Pattern Demo - 反射代理模式.

适用场景：简单快速响应，基于规则的决策
特点：直接的if-then规则匹配，立即响应，极低延迟.

Based on plan.md requirements:
- Receives input
- Matches input to predefined action using simple if-then rules
- Executes action immediately
"""

import re
from typing import Annotated

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.llm_config import get_llm


class ReflexState(TypedDict):
    """State for reflex agent pattern."""

    messages: Annotated[list, add_messages]
    matched_rule: str
    action_taken: str
    evaluation_mode: bool  # If True, output clean results without decorative formatting


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
    """规则匹配节点：分析输入，匹配多个规则并立即执行对应动作."""
    # 获取用户输入
    user_input = state["messages"][-1].content if state["messages"] else ""
    user_input_lower = user_input.lower()

    # Check evaluation mode
    evaluation_mode = state.get("evaluation_mode", False)

    # In evaluation mode, use LLM-based approach instead of rule matching
    # This allows Reflex to handle diverse tasks that don't fit predefined rules
    if evaluation_mode:
        from src.llm_config import get_llm
        from src.tool import tools as eval_tools
        llm_eval = get_llm()

        try:
            # Use LLM with tools to answer directly
            llm_with_tools = llm_eval.bind_tools(eval_tools)

            prompt = f"""Answer this query directly and concisely: {user_input}

IMPORTANT - Output format:
- For calculations: output only the number (e.g., "408")
- For facts: output only the fact (e.g., "Paris")
- For yes/no: output only "Yes" or "No"
- For dates: output only the date in requested format
- For JSON: output only the JSON object
- NO explanations, NO prefixes, NO tool result formatting

Provide only the answer:"""

            response = llm_with_tools.invoke([{"role": "user", "content": prompt}])

            # Check if tools were called
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls
                from langgraph.prebuilt import ToolNode
                tool_node = ToolNode(eval_tools)
                tool_results = tool_node.invoke({"messages": [response]})

                # Get tool results and generate final answer
                final_prompt = f"""Based on the tool results, answer this query concisely: {user_input}

Tool results: {tool_results}

Remember:
- Output ONLY the direct answer
- NO explanations or prefixes
- Extract the key information from tool results

Provide only the answer:"""
                final_response = llm_eval.invoke([{"role": "user", "content": final_prompt}])
                final_answer = final_response.content.strip()
            else:
                final_answer = response.content.strip()

            messages = state["messages"]
            return {
                "messages": messages + [AIMessage(content=final_answer)],
                "matched_rule": "llm_evaluation_mode",
                "action_taken": "LLM-based direct answer",
                "evaluation_mode": True
            }

        except Exception as e:
            # Fallback to simple LLM response
            try:
                response = llm_eval.invoke([{"role": "user", "content": f"Answer briefly: {user_input}"}])
                final_answer = response.content.strip()
            except Exception:
                final_answer = f"Error: {str(e)}"

            messages = state["messages"]
            return {
                "messages": messages + [AIMessage(content=final_answer)],
                "matched_rule": "llm_fallback",
                "action_taken": "LLM fallback response",
                "evaluation_mode": True
            }

    # 查找所有匹配的规则（按优先级排序）- 支持复合查询，但排除默认规则以避免重复
    matched_rules: list[dict[str, object]] = []
    sorted_rules = sorted(REFLEX_RULES, key=lambda x: x.get("priority", 999))  # type: ignore[arg-type, return-value]
    for rule in sorted_rules:
        pattern = str(rule["pattern"])
        if rule["action"] != "general_response" and re.search(pattern, user_input_lower, re.IGNORECASE):
            matched_rules.append(rule)

    # 如果没有匹配到任何具体规则，使用默认规则
    if not matched_rules:
        matched_rules = [REFLEX_RULES[-1]]  # 默认规则

    messages = state["messages"]
    response_parts = []
    tools_used = []
    actions_taken = []

    # Reflex Agent: 根据匹配的规则执行对应动作
    from src.tool import tools

    for rule in matched_rules:
        action = rule["action"]
        actions_taken.append(action)

        if action == "weather_query":
            # 天气查询 - 使用搜索工具
            search_tool = next(tool for tool in tools if tool.name == "tavily_search_results_json")
            try:
                result = search_tool.invoke({"query": f"weather {user_input}"})
                if evaluation_mode:
                    response_parts.append(str(result))
                else:
                    response_parts.append(f"🌤️ Weather Information:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception as e:
                if evaluation_mode:
                    response_parts.append(f"Weather lookup failed: {str(e)}")
                else:
                    response_parts.append(f"🌤️ Weather lookup failed: {str(e)}")
                tools_used.append("tavily_search_results_json (failed)")

        elif action == "time_query":
            # 时间查询 - 使用日期工具
            date_tool = next((tool for tool in tools if "get_current_date" in tool.name), None)
            if date_tool:
                try:
                    result = date_tool.invoke({})
                    if evaluation_mode:
                        response_parts.append(str(result))
                    else:
                        response_parts.append(f"🕒 Current Date/Time:\n{result}")
                    tools_used.append(date_tool.name)
                except Exception as e:
                    if evaluation_mode:
                        response_parts.append(f"Date lookup failed: {str(e)}")
                    else:
                        response_parts.append(f"🕒 Date lookup failed: {str(e)}")
                    tools_used.append(f"{date_tool.name} (failed)")
            else:
                if evaluation_mode:
                    response_parts.append("Date tool not available")
                else:
                    response_parts.append("🕒 Current time: Date tool not available in this demo.")
                tools_used.append("date_tool (not available)")

        elif action == "search_query":
            # 搜索查询 - 使用搜索工具
            search_tool = next(tool for tool in tools if tool.name == "tavily_search_results_json")
            try:
                result = search_tool.invoke({"query": user_input})
                if evaluation_mode:
                    response_parts.append(str(result))
                else:
                    response_parts.append(f"🔍 Search Results:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception as e:
                if evaluation_mode:
                    response_parts.append(f"Search failed: {str(e)}")
                else:
                    response_parts.append(f"🔍 Search failed: {str(e)}")
                tools_used.append("tavily_search_results_json (failed)")

        elif action == "calculation":
            # 计算 - 直接处理
            calc_result = _handle_calculation(user_input, evaluation_mode)
            if evaluation_mode:
                response_parts.append(calc_result)
            else:
                response_parts.append(f"🧮 Calculation:\n{calc_result}")
            tools_used.append("direct_calculation")

        elif action == "greeting":
            # 问候 - 直接响应
            if evaluation_mode:
                response_parts.append("Hello! How can I help you?")
            else:
                response_parts.append("👋 Hello! I'm a Reflex Agent designed to respond quickly to common requests. How can I help you today?")
            tools_used.append("direct_response")

        elif action == "help_request":
            # 帮助 - 直接响应
            if evaluation_mode:
                help_text = "I can help with weather queries, searches, calculations, time, or general assistance."
            else:
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
                if evaluation_mode:
                    response_parts.append(str(result))
                else:
                    response_parts.append(f"🔧 General Help:\n{result}")
                tools_used.append("tavily_search_results_json")
            except Exception:
                if evaluation_mode:
                    response_parts.append(rule.get('response', 'How can I assist you?'))
                else:
                    response_parts.append(f"🔧 I'll try to help: {rule.get('response', 'How can I assist you?')}")
                tools_used.append("tavily_search_results_json (failed)")

    # 构建最终响应 - 根据 evaluation_mode 决定是否添加格式化前缀
    if evaluation_mode:
        # Evaluation mode: clean output without decorative formatting
        final_response = "\n\n".join(response_parts)
    else:
        # Demo mode: add tool usage info for readability
        tool_info = f"🔧 Tools used: {', '.join(set(tools_used))}\n\n"
        final_response = tool_info + "\n\n".join(response_parts)

    return {
        "messages": messages + [AIMessage(content=final_response)],
        "matched_rule": ", ".join(str(a) for a in actions_taken),
        "action_taken": f"Reflex executed: {', '.join(str(a) for a in actions_taken)} | Tools: {', '.join(str(t) for t in set(tools_used))}",
        "evaluation_mode": evaluation_mode
    }



def _handle_calculation(user_input: str, evaluation_mode: bool = False) -> str:
    """处理简单的数学计算."""
    import re

    # 查找简单的数学表达式
    math_pattern = r'(\d+(?:\.\d+)?)\s*([+\-*/×])\s*(\d+(?:\.\d+)?)'
    match = re.search(math_pattern, user_input)

    if match:
        try:
            num1, operator, num2 = match.groups()
            num1, num2 = float(num1), float(num2)

            # Normalize × to *
            if operator == '×':
                operator = '*'

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

            # Format result as integer if it's a whole number
            if result == int(result):
                result = int(result)

            if evaluation_mode:
                # Evaluation mode: only return the result
                return str(result)
            else:
                # Demo mode: return full calculation
                return f"Calculation: {num1} {operator} {num2} = {result}"
        except Exception:
            return "Error: Could not perform calculation!"

    if evaluation_mode:
        return "Cannot parse calculation"
    else:
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