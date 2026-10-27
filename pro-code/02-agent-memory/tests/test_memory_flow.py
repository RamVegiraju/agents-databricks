"""Offline behavioral tests: execute real LangGraph loops with injected model/store boundaries."""

from types import SimpleNamespace

import pytest
from databricks.sdk.errors import AlreadyExists
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.agent import build_graph
from agent.memory import selected_memory_tools
from agent.transcript import message_items, persist_turn, transcript_session_id


class ScriptedModel:
    """A deterministic model boundary; real graph/tool execution remains enabled."""

    def __init__(self, tool: str, args: dict):
        self.tool, self.args = tool, args

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content=str(messages[-1].content))
        return AIMessage(
            content="",
            tool_calls=[{"name": self.tool, "args": self.args, "id": "call-1"}],
        )


class MemoryStore:
    def __init__(self):
        self.entries = {}

    def put(self, *, actor_id, path, content, append=False):
        self.entries[(actor_id, path)] = SimpleNamespace(
            path=path, content=content, session_id=None
        )

    def search(self, *, actor_id, query, limit, session_id=None):
        return [
            SimpleNamespace(memory=m)
            for (actor, _), m in self.entries.items()
            if actor == actor_id and query.lower() in m.content.lower()
        ][:limit]

    def list(self, *, actor_id, path=None, session_id=None, page_size=None):
        entries = []
        for (actor, key), entry in self.entries.items():
            if actor != actor_id or (path is not None and key != path):
                continue
            entry.update = lambda content, description=None, e=entry: setattr(
                e, "content", content
            )
            entry.delete = lambda k=(actor, key): self.entries.pop(k)
            entry.description = "preferences"
            entries.append(entry)
        return entries


@pytest.mark.asyncio
async def test_explicit_save_then_cross_conversation_recall_and_actor_isolation(
    monkeypatch,
):
    from databricks_agentkit.langgraph import memory

    store = MemoryStore()
    monkeypatch.setenv("AGENT_MEMORY_STORE", "test-store")
    monkeypatch.setenv("MEMORY_WRITE_MODE", "tools")
    monkeypatch.setattr(memory, "workspace_client", lambda: None)
    monkeypatch.setattr(
        memory,
        "AgentKitClient",
        lambda _: SimpleNamespace(
            memory_stores=SimpleNamespace(_handle=lambda _: store)
        ),
    )
    saver = InMemorySaver()
    write = build_graph(
        ScriptedModel("remember", {"fact": "Prefers Python", "topic": "preferences"}),
        selected_memory_tools("alice"),
        saver,
    )
    await write.ainvoke(
        {"messages": [HumanMessage("Remember Python")]},
        {"configurable": {"thread_id": "chat-A"}},
    )
    read = build_graph(
        ScriptedModel("recall", {"query": "Python"}),
        selected_memory_tools("alice"),
        saver,
    )
    result = await read.ainvoke(
        {"messages": [HumanMessage("What language?")]},
        {"configurable": {"thread_id": "chat-B"}},
    )
    assert "Prefers Python" in result["messages"][-1].content
    other = build_graph(
        ScriptedModel("recall", {"query": "Python"}),
        selected_memory_tools("bob"),
        saver,
    )
    result = await other.ainvoke(
        {"messages": [HumanMessage("What language?")]},
        {"configurable": {"thread_id": "chat-C"}},
    )
    assert result["messages"][-1].content == "No relevant memories."


def test_pipeline_mode_omits_writers_and_actor_is_not_a_model_parameter(monkeypatch):
    monkeypatch.setenv("AGENT_MEMORY_STORE", "test-store")
    monkeypatch.setenv("MEMORY_WRITE_MODE", "pipeline")
    tools = selected_memory_tools("alice")
    assert {tool.name for tool in tools} == {"recall", "list_memories"}
    assert all(
        "actor" not in str(tool.args_schema.model_json_schema()["properties"])
        for tool in tools
    )


@pytest.mark.asyncio
async def test_released_list_and_forget_tools_support_correction(monkeypatch):
    from databricks_agentkit.langgraph import memory

    store = MemoryStore()
    monkeypatch.setenv("AGENT_MEMORY_STORE", "test-store")
    monkeypatch.setenv("MEMORY_WRITE_MODE", "tools")
    monkeypatch.setattr(memory, "workspace_client", lambda: None)
    monkeypatch.setattr(
        memory,
        "AgentKitClient",
        lambda _: SimpleNamespace(
            memory_stores=SimpleNamespace(_handle=lambda _: store)
        ),
    )
    tools = {t.name: t for t in selected_memory_tools("alice")}
    await tools["remember"].ainvoke({"fact": "Prefers Python", "topic": "preferences"})
    assert "/preferences.md" in await tools["list_memories"].ainvoke({})
    result = await tools["forget"].ainvoke(
        {"fact": "Prefers Python", "topic": "preferences"}
    )
    assert "Forgot 1 fact" in result
    await tools["remember"].ainvoke({"fact": "Prefers Rust", "topic": "preferences"})
    assert "Prefers Rust" in await tools["recall"].ainvoke({"query": "Rust"})
    assert await tools["recall"].ainvoke({"query": "Python"}) == "No relevant memories."


@pytest.mark.asyncio
async def test_system_memory_context_is_not_checkpointed():
    from langchain_core.tools import tool

    @tool
    def greet() -> str:
        """Say hello locally."""
        return "hello"

    graph = build_graph(
        ScriptedModel("greet", {}),
        [greet],
        InMemorySaver(),
        prompt="Retrieved private preference",
    )
    config = {"configurable": {"thread_id": "no-context-leak"}}
    result = await graph.ainvoke({"messages": [HumanMessage("Hello")]}, config)
    assert all(m.type != "system" for m in result["messages"])
    snapshot = await graph.aget_state(config)
    assert "Retrieved private preference" not in str(snapshot.values)


class TranscriptStore:
    def __init__(self):
        self.sessions = {}

    def add(self, *, actor_id, session_id, metadata):
        if session_id in self.sessions:
            raise AlreadyExists("exists")
        items = []
        session = SimpleNamespace(
            actor_id=actor_id,
            metadata=metadata,
            list_items=lambda **_: [SimpleNamespace(data=i) for i in items],
            append_items=lambda new: items.extend(new),
        )
        self.sessions[session_id] = session
        return session

    def get(self, session_id):
        return self.sessions[session_id]


def test_transcript_is_pipeline_readable_and_replay_does_not_duplicate():
    store = TranscriptStore()
    messages = [
        {"role": "user", "content": "I prefer Python"},
        {"type": "tool", "content": "skip"},
        {"type": "ai", "content": "Understood"},
    ]
    persist_turn(store, "alice", "chat-A", "inv-1", messages)
    persist_turn(store, "alice", "chat-A", "inv-1", messages)
    session = store.get(transcript_session_id("alice", "inv-1"))
    assert [i.data for i in session.list_items()] == [
        {"type": "message", "role": "user", "content": "I prefer Python"},
        {"type": "message", "role": "assistant", "content": "Understood"},
    ]
    assert session.actor_id == "alice"
    assert session.metadata["source_session_id"] == "chat-A"
    assert transcript_session_id("alice", "inv-1") != transcript_session_id(
        "bob", "inv-1"
    )
    with pytest.raises(ValueError, match="differs"):
        persist_turn(
            store, "alice", "chat-A", "inv-1", [{"role": "user", "content": "changed"}]
        )


def test_transcript_checks_existing_actor():
    store = TranscriptStore()
    store.sessions[transcript_session_id("alice", "inv-1")] = SimpleNamespace(
        actor_id="bob"
    )
    with pytest.raises(PermissionError):
        persist_turn(
            store, "alice", "chat-A", "inv-1", [{"role": "user", "content": "Hello"}]
        )


def test_pipeline_transcript_excludes_system_and_tool_messages():
    assert (
        message_items(
            [
                {"role": "system", "content": "secret system prompt"},
                {"role": "tool", "content": "tool data"},
            ]
        )
        == []
    )
