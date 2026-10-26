"""A local Python tool the LangGraph agent can call."""

from datetime import UTC, datetime

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """Get the current date and time in UTC."""
    return datetime.now(UTC).isoformat()
