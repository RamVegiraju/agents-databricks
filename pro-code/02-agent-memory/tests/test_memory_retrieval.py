"""Check automatic and tool-driven retrieval at the managed-store boundary."""

from types import SimpleNamespace
from typing import Any

import pytest

from agent import memory


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enabled", "store_id", "query"),
    [("false", "store", "Cedar"), ("true", "", "Cedar"), ("true", "store", "")],
)
async def test_automatic_recall_skips_remote_calls_when_unavailable(
    monkeypatch: pytest.MonkeyPatch, enabled: str, store_id: str, query: str
) -> None:
    monkeypatch.setenv("MEMORY_AUTO_RECALL", enabled)
    monkeypatch.setenv("AGENT_MEMORY_STORE", store_id)
    monkeypatch.setattr(
        memory, "workspace_client", lambda: pytest.fail("Unexpected workspace call")
    )
    assert await memory.recalled_context("alice", query) == ""


@pytest.mark.asyncio
async def test_automatic_recall_searches_each_input_with_trusted_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    selected_stores: list[str] = []

    def search(**kwargs: Any) -> list[Any]:
        calls.append(kwargs)
        return [
            SimpleNamespace(
                memory=SimpleNamespace(
                    path="projects/cedar.md", content="Concise Python"
                )
            )
        ]

    def get_store(store_id: str) -> Any:
        selected_stores.append(store_id)
        return SimpleNamespace(search=search)

    monkeypatch.setenv("MEMORY_AUTO_RECALL", "true")
    monkeypatch.setenv("AGENT_MEMORY_STORE", "bound-memory")
    monkeypatch.setattr(memory, "workspace_client", lambda: None)
    monkeypatch.setattr(
        memory,
        "AgentKitClient",
        lambda _: SimpleNamespace(memory_stores=SimpleNamespace(get=get_store)),
    )
    assert (
        await memory.recalled_context("alice", "Cedar preferences")
        == "projects/cedar.md: Concise Python"
    )
    await memory.recalled_context("alice", "Cedar coding style")
    assert selected_stores == ["bound-memory", "bound-memory"]
    assert calls == [
        {"actor_id": "alice", "query": "Cedar preferences", "limit": 5},
        {"actor_id": "alice", "query": "Cedar coding style", "limit": 5},
    ]


@pytest.mark.asyncio
async def test_automatic_recall_handles_no_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORY_AUTO_RECALL", "true")
    monkeypatch.setenv("AGENT_MEMORY_STORE", "bound-memory")
    monkeypatch.setattr(memory, "workspace_client", lambda: None)
    monkeypatch.setattr(
        memory,
        "AgentKitClient",
        lambda _: SimpleNamespace(
            memory_stores=SimpleNamespace(
                get=lambda _: SimpleNamespace(search=lambda **_: [])
            )
        ),
    )
    assert await memory.recalled_context("alice", "Cedar preferences") == ""


@pytest.mark.asyncio
async def test_recall_tool_scopes_query_limit_and_optional_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from databricks_agentkit.langgraph import memory as adapter

    calls: list[dict[str, Any]] = []

    def search(**kwargs: Any) -> list[Any]:
        calls.append(kwargs)
        return []

    monkeypatch.setenv("AGENT_MEMORY_STORE", "bound-memory")
    monkeypatch.setenv("MEMORY_WRITE_MODE", "pipeline")
    monkeypatch.setattr(adapter, "workspace_client", lambda: None)
    monkeypatch.setattr(
        adapter,
        "AgentKitClient",
        lambda _: SimpleNamespace(
            memory_stores=SimpleNamespace(
                _handle=lambda _: SimpleNamespace(search=search)
            )
        ),
    )
    tools = {tool.name: tool for tool in memory.selected_memory_tools("alice")}
    assert await tools["recall"].ainvoke({"query": "Cedar"}) == "No relevant memories."
    await tools["recall"].ainvoke({"query": "Cedar", "session_id": "source-session"})
    assert calls == [
        {"actor_id": "alice", "query": "Cedar", "limit": 5, "session_id": None},
        {
            "actor_id": "alice",
            "query": "Cedar",
            "limit": 5,
            "session_id": "source-session",
        },
    ]
