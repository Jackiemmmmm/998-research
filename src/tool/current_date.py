"""Current date tool module.

This module provides a tool to get the current date.
"""

import datetime

from langchain_core.tools import tool


@tool
def get_current_date() -> str:
    """Get the current date.

    Returns:
        the current date, format as YYYY-MM-DD
    """
    return datetime.datetime.today().strftime("%Y-%m-%d")
