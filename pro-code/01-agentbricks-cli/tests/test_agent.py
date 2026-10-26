"""Exercise the LangGraph model/tool loop without a workspace connection."""

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.agent import build_graph


class ClockModel:
    def bind_tools(self, tools):
        assert {tool.name for tool in tools} == {"get_current_time"}
        return self

    async def ainvoke(self, messages):
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="The clock tool completed.")
        return AIMessage(
            content="",
            tool_calls=[{"name": "get_current_time", "args": {}, "id": "clock-call"}],
        )


@pytest.mark.asyncio
async def test_graph_calls_local_clock_tool():
    graph = build_graph(ClockModel(), InMemorySaver())
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "What time is it?"}]},
        {"configurable": {"thread_id": "test-clock"}},
    )

    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert result["messages"][-1].content == "The clock tool completed."
