"""Exercise the MCP tool path with a local stand-in for the remote service."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from agent.agent import build_graph


@tool
def web_search(query: str) -> str:
    """Return a search result for a query."""
    return f"Source: https://example.com/release-notes for {query}"


class ResearchModel:
    def __init__(self):
        self.calls = 0

    def bind_tools(self, tools):
        assert tools == [web_search]
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "web_search",
                        "args": {"query": "LangGraph release notes"},
                        "id": "search-1",
                    }
                ],
            )
        assert any(isinstance(message, ToolMessage) for message in messages)
        return AIMessage(content="See https://example.com/release-notes")


@pytest.mark.asyncio
async def test_graph_executes_bound_search_tool():
    graph = build_graph(ResearchModel(), None, [web_search])
    result = await graph.ainvoke({"messages": [HumanMessage(content="What's new?")]})
    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert result["messages"][-1].content == "See https://example.com/release-notes"
