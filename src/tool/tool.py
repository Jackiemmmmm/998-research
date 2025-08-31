from langchain_tavily import TavilySearch
from .current_date import get_current_date

tool = TavilySearch(max_results=2)

tools = [tool, get_current_date]
