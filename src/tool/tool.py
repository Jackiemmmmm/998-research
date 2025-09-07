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
    """A mock search tool for demonstration purposes when Tavily API is not available."""
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
        print("✅ Using Tavily search tool (community version)")
    except Exception as e:
        print(f"Warning: Could not initialize Tavily search tool: {e}")
        print("Using mock search tool instead")
        search_tool = mock_search
else:
    print("ℹ️  No TAVILY_API_KEY found, using mock search tool")

tools = [search_tool, get_current_date]
