"""Offline integration checks: SDK serialization, citations and a real graph tool loop."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from databricks.sdk.service import vectorsearch as v
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent.tools.policy_search import build_policy_tools, decode_hits
from scripts.create_search_index import index_spec
from scripts.ingest_policies import ingest, policy_chunks, sql_name
from scripts.register_mcp import apply_registration, registration


def test_invocation_actor_is_server_owned(monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.adapter import _actor

    monkeypatch.setenv("DEMO_ACTOR_ID", "retail-demo")
    assert _actor({"actor": "somebody-else"}, "session-1") == "retail-demo"
    assert _actor({}, "session-2") == "retail-demo"


def response() -> v.QueryVectorIndexResponse:
    """Use the actual SDK response deserializer, including a non-leading citation column."""
    return v.QueryVectorIndexResponse.from_dict(
        {
            "manifest": {
                "columns": [
                    {"name": name}
                    for name in ["content", "source_uri", "chunk_id", "title", "score"]
                ]
            },
            "result": {
                "data_array": [
                    [
                        "Returns within 30 days",
                        "northstar-policy://returns.md",
                        "chunk-1",
                        "Returns",
                        0.91,
                    ]
                ]
            },
        }
    )


@pytest.mark.asyncio
async def test_search_uses_sdk_hybrid_and_preserves_citations() -> None:
    query = Mock(return_value=response())
    client = SimpleNamespace(vector_search_indexes=SimpleNamespace(query_index=query))
    search = build_policy_tools(
        client_factory=lambda: client, index_name="demo.retail.policies"
    )[0]
    result = await search.ainvoke({"query": "return Rain Shell"})
    assert result["matches"][0]["source_uri"] == "northstar-policy://returns.md"
    assert result["matches"][0]["chunk_id"] == "chunk-1"
    query.assert_called_once_with(
        index_name="demo.retail.policies",
        query_text="return Rain Shell",
        query_type="HYBRID",
        columns=["chunk_id", "content", "source_uri", "title"],
        num_results=4,
    )


@pytest.mark.asyncio
async def test_search_reports_missing_config_and_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POLICY_INDEX_NAME", raising=False)
    client_factory = Mock(side_effect=AssertionError("must not resolve auth"))
    search = build_policy_tools(client_factory=client_factory)[0]
    with pytest.raises(ValueError, match="POLICY_INDEX_NAME"):
        await search.ainvoke({"query": "returns"})
    client_factory.assert_not_called()
    failing = build_policy_tools(
        client_factory=Mock(side_effect=RuntimeError("permission denied")),
        index_name="a.b.c",
    )[0]
    with pytest.raises(RuntimeError, match="permission denied"):
        await failing.ainvoke({"query": "returns"})


def test_decode_empty_results_without_fabrication() -> None:
    assert (
        decode_hits(
            v.QueryVectorIndexResponse.from_dict({"result": {"data_array": []}})
        )
        == []
    )


def test_chunks_and_index_spec_have_consistent_columns() -> None:
    chunks = policy_chunks()
    assert len(chunks) == 3
    assert chunks == policy_chunks()
    assert len({c["chunk_id"] for c in chunks}) == 3
    spec = index_spec("demo.retail.policy_chunks", "databricks-gte-large-en").as_dict()
    assert spec["pipeline_type"] == "TRIGGERED"
    assert set(spec["columns_to_sync"]) == set(chunks[0])
    assert spec["embedding_source_columns"][0]["name"] == "content"
    with pytest.raises(ValueError):
        sql_name("demo.retail.table; DROP TABLE x")


def test_registration_uses_schema_connection_and_service_without_token_leak() -> None:
    plan = registration("demo.retail", "github_readonly", "github_docs")
    assert "bearer_token" not in json.dumps(plan)
    w = SimpleNamespace(
        connections=SimpleNamespace(create=Mock()),
        ai_gateway=SimpleNamespace(create_mcp_service=Mock()),
    )
    apply_registration(w, plan, "test-only-secret")
    connection = w.connections.create.call_args.kwargs
    assert connection["parent"] == "schemas/demo.retail"
    assert connection["options"]["base_path"] == "/mcp/readonly"
    assert connection["options"]["bearer_token"] == "test-only-secret"
    service = w.ai_gateway.create_mcp_service.call_args.kwargs
    config = service["mcp_service"].as_dict()["config"]
    assert (
        config["source_connection"]["name"] == "connections/demo.retail.github_readonly"
    )
    assert config["include_tool_selectors"] == ["get_file_contents", "search_code"]


def test_ingestion_parameterizes_document_text_and_enables_cdf() -> None:
    from databricks.sdk.service.sql import StatementResponse

    execute = Mock(
        return_value=StatementResponse.from_dict({"status": {"state": "SUCCEEDED"}})
    )
    w = SimpleNamespace(statement_execution=SimpleNamespace(execute_statement=execute))
    chunk = {
        "chunk_id": "1",
        "content": "customer's document; not SQL",
        "source_uri": "policy://test",
        "title": "Test",
    }
    ingest(w, "warehouse", "demo.retail.chunks", [chunk])
    calls = [call.kwargs for call in execute.call_args_list]
    assert "delta.enableChangeDataFeed = true" in calls[0]["statement"]
    assert calls[2]["statement"].startswith("MERGE INTO `demo`.`retail`.`chunks`")
    assert chunk["content"] not in calls[2]["statement"]
    assert {p.name: p.value for p in calls[2]["parameters"]} == chunk
    assert calls[2]["on_wait_timeout"].value == "CANCEL"


@pytest.mark.parametrize(
    "module_name", ["ingest_policies", "create_search_index", "register_mcp"]
)
def test_setup_default_preview_never_constructs_workspace_client(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import importlib

    module = importlib.import_module(f"scripts.{module_name}")
    forbidden = Mock(side_effect=AssertionError("preview must remain offline"))
    monkeypatch.setattr(module, "WorkspaceClient", forbidden)
    monkeypatch.setattr("sys.argv", [module_name])
    module.main()
    assert json.loads(capsys.readouterr().out)
    forbidden.assert_not_called()


class ToolCallingModel(BaseChatModel):
    """A deterministic model that requests retrieval and then reads its actual result."""

    @property
    def _llm_type(self) -> str:
        return "offline-tool-calling-test"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ToolCallingModel:
        assert "search_policies" in {tool.name for tool in tools}
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if isinstance(messages[-1], ToolMessage):
            observation = json.loads(messages[-1].content)
            answer = AIMessage(content=observation["matches"][0]["source_uri"])
        else:
            answer = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_policies",
                        "args": {"query": "returns"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=answer)])


@pytest.mark.asyncio
async def test_production_graph_executes_search_and_returns_observed_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    import agent.agent as app

    query = Mock(return_value=response())
    search_tools = build_policy_tools(
        client_factory=lambda: SimpleNamespace(
            vector_search_indexes=SimpleNamespace(query_index=query)
        ),
        index_name="demo.retail.policy_index",
    )
    monkeypatch.setattr(
        app, "_RoutedChatDatabricks", lambda **kwargs: ToolCallingModel()
    )
    monkeypatch.setattr(app, "workspace_client", lambda: None)
    monkeypatch.setattr(app, "build_policy_tools", lambda: search_tools)
    monkeypatch.setattr(app, "mcp_tools", AsyncMock(return_value=[]))
    monkeypatch.setattr(app, "genie_tools", lambda **kwargs: [])
    monkeypatch.setattr(app, "memory_tools", lambda actor: [])
    monkeypatch.setattr(app, "checkpointer", lambda: InMemorySaver())
    graph = await app.create_agent_graph("alice")
    output = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Returns?"}]},
        config={"configurable": {"thread_id": "test"}},
    )
    query.assert_called_once()
    assert output["messages"][-1].content == "northstar-policy://returns.md"
    assert any(isinstance(message, ToolMessage) for message in output["messages"])
