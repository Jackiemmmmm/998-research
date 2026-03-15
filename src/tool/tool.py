"""Tool definitions for agent.

This module defines tools available to agents, including search and date tools.
"""

import os
from pathlib import Path

from langchain_core.tools import tool

from .current_date import get_current_date

# 确保加载环境变量
try:
    from dotenv import load_dotenv
    # 查找.env文件 - 从当前文件向上查找到项目根目录
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent  # src/tool/tool.py -> 项目根目录
    env_file = project_root / '.env'
    
    if env_file.exists():
        load_dotenv(env_file)
        # print(f"✅ Loaded environment from: {env_file}")
    else:
        load_dotenv()  # 尝试从默认位置加载
except ImportError:
    pass  # 如果没有python-dotenv，忽略

@tool
def mock_search(query: str) -> str:
    """Return mock search results for demonstration purposes.

    Use this when Tavily API is not available.
    """
    return f"Mock search results for: {query}\n- Demo result 1: Information about {query}\n- Demo result 2: Additional context about {query}"

# 尝试使用Tavily搜索工具
search_tool = mock_search  # 默认使用mock

if os.getenv("TAVILY_API_KEY"):
    try:
        # 使用社区版本（功能完整，虽有deprecation警告但依然可用）
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # 临时抑制deprecation警告
            from langchain_community.tools import TavilySearchResults
            search_tool = TavilySearchResults(max_results=2)
    except Exception:
        search_tool = mock_search
else:
    pass

# --- Mock tools for evaluation tasks C1-C4 ---

@tool
def weather_api(city: str) -> str:
    """Get current weather for a city (mocked). Returns JSON with temp and condition."""
    import json
    mock_data = {
        "rome": {"temp": 28, "condition": "Sunny"},
        "london": {"temp": 15, "condition": "Cloudy"},
        "tokyo": {"temp": 22, "condition": "Rainy"},
        "new york": {"temp": 18, "condition": "Partly Cloudy"},
    }
    result = mock_data.get(city.lower(), {"temp": 20, "condition": "Clear"})
    return json.dumps(result)


@tool
def fx_api(from_currency: str, to_currency: str) -> str:
    """Get mocked foreign exchange rate between two currencies. Returns JSON with rate."""
    import json
    mock_rates = {
        ("USD", "EUR"): 0.90,
        ("EUR", "USD"): 1.11,
        ("USD", "GBP"): 0.79,
        ("GBP", "USD"): 1.27,
    }
    pair = (from_currency.upper(), to_currency.upper())
    rate = mock_rates.get(pair, 1.0)
    return json.dumps({"rate": rate})


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple math expression. E.g. '100 * 0.90' returns '90.0'."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def wiki_search(query: str) -> str:
    """Search a mocked encyclopedia/wikipedia. Returns JSON with key facts."""
    import json
    mock_entries = {
        "penicillin": {"name": "Alexander Fleming", "year": 1928},
        "alexander fleming": {"name": "Alexander Fleming", "year": 1928},
        "relativity": {"name": "Albert Einstein", "year": 1905},
        "telephone": {"name": "Alexander Graham Bell", "year": 1876},
    }
    for key, value in mock_entries.items():
        if key in query.lower():
            return json.dumps(value)
    return json.dumps({"name": "Unknown", "year": 0})


@tool
def shopping_search(query: str) -> str:
    """Search for products in a mocked shopping catalog. Returns JSON with url and price."""
    import json
    mock_products = {
        "usb-c": {"url": "https://shop.example/u1", "price": 9.5},
        "usb c": {"url": "https://shop.example/u1", "price": 9.5},
        "cable": {"url": "https://shop.example/u1", "price": 9.5},
        "hdmi": {"url": "https://shop.example/h1", "price": 12.0},
    }
    for key, value in mock_products.items():
        if key in query.lower():
            return json.dumps(value)
    return json.dumps({"url": "https://shop.example/default", "price": 0.0})


tools = [search_tool, get_current_date, weather_api, fx_api, calculator, wiki_search, shopping_search]
