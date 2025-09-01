from langchain_tavily import TavilySearch
from .current_date import get_current_date

search_tool = TavilySearch(max_results=2)

tools = [search_tool, get_current_date]
