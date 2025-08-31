import datetime
from langchain.tools import tool


@tool
def get_current_date() -> str:
    """
    get the current date

    Returns:
        the current date, format as YYYY-MM-DD
    """
    return datetime.datetime.today().strftime("%Y-%m-%d")
