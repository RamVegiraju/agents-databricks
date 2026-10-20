"""Offline behavioral checks: routing, both-domain evidence, scope, and SDK calls."""

from types import SimpleNamespace

import pytest
from databricks_agentkit.runtime.genie import GenieAgent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from agent.supervisor import build_supervisor, specialist_tools


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.asyncio
async def test_supervisor_consults_both_and_synthesizes():
    calls = []

    @tool
    async def sales_specialist(question: str) -> str:
        """Sales evidence."""
        calls.append(("sales", question))
        return "SKU-100 sold 18 units, 2026-10-01 to 2026-10-03."

    @tool
    async def inventory_specialist(question: str) -> str:
        """Inventory evidence."""
        calls.append(("inventory", question))
        return "SKU-100 on_hand_units=4, reorder_point_units=10, snapshot 2026-10-03."

    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "sales_specialist",
                        "args": {"question": "Sales by product Oct 1–3 2026"},
                        "id": "s1",
                    },
                    {
                        "name": "inventory_specialist",
                        "args": {"question": "Stock by product on Oct 3 2026"},
                        "id": "i1",
                    },
                ],
            ),
            AIMessage(
                content="SKU-100: 18 sold; 4 on hand below its reorder point of 10."
            ),
        ]
    )
    graph = build_supervisor(
        model, [sales_specialist, inventory_specialist], checkpointer=InMemorySaver()
    )
    result = await graph.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Which popular products need replenishment?",
                }
            ]
        },
        {"configurable": {"thread_id": "offline-session"}},
    )
    assert {domain for domain, _ in calls} == {"sales", "inventory"}
    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert len(tool_messages) == 2
    assert "reorder point" in result["messages"][-1].text


def test_missing_domain_binding_is_actionable():
    with pytest.raises(ValueError, match="--name sales"):
        specialist_tools(ScriptedModel(responses=[AIMessage(content="unused")]), [])


@pytest.mark.asyncio
async def test_native_genie_uses_injected_sdk_and_reads_query_rows():
    """Exercise real AgentKit Genie adapter against a stub of WorkspaceClient.genie."""
    space, conversation, message, attachment = (f"{i:032x}" for i in range(1, 5))
    calls = []

    class Response:
        def __init__(self, value):
            self.value = value

        def as_dict(self):
            return self.value

    class SDK:
        def start_conversation(self, space_id, question):
            calls.append((space_id, question))
            return SimpleNamespace(
                response=SimpleNamespace(
                    conversation_id=conversation, message_id=message
                )
            )

        def get_message(self, *args):
            return Response(
                {
                    "status": "COMPLETED",
                    "attachments": [
                        {
                            "attachment_id": attachment,
                            "query": {"query": "SELECT SUM(units) FROM sales"},
                        }
                    ],
                }
            )

        def get_message_attachment_query_result(self, *args):
            assert args == (space, conversation, message, attachment)
            return Response(
                {
                    "statement_response": {
                        "status": {"state": "SUCCEEDED"},
                        "manifest": {
                            "total_row_count": 1,
                            "schema": {"columns": [{"name": "units"}]},
                        },
                        "result": {"data_array": [["18"]]},
                    }
                }
            )

    client = SimpleNamespace(
        genie=SDK(), config=SimpleNamespace(host="https://offline.invalid")
    )
    genie = GenieAgent(space, workspace_client_for=lambda auth: client)
    answer = await genie.ask("How many units sold?")
    rows = await genie.query_result(
        answer["conversation_id"], answer["message_id"], attachment
    )
    assert calls == [(space, "How many units sold?")]
    assert rows["rows"] == [["18"]]
    assert not rows["truncated"]


@pytest.mark.asyncio
async def test_sales_specialist_does_not_receive_inventory_tools():
    captured = []
    model = ScriptedModel(responses=[AIMessage(content="No fabricated data.")])
    native = []
    for domain in ("sales", "inventory"):
        for method in ("ask", "poll", "query_result"):

            @tool(f"{domain}_{method}")
            async def stub(question: str = "unused") -> str:
                """Offline native tool stub."""
                return "unused"

            native.append(stub)

    # Capture tool definitions when the actual specialist graph binds its model.
    original = ScriptedModel.bind_tools

    def bind(self, tools, **kwargs):
        captured.append({t.name for t in tools})
        return original(self, tools, **kwargs)

    from unittest.mock import patch

    with patch.object(ScriptedModel, "bind_tools", bind):
        delegates = specialist_tools(model, native)
        await delegates[0].ainvoke({"question": "Sales only"})
    assert captured == [{"sales_ask", "sales_poll", "sales_query_result"}]


def test_manifest_builds_both_native_tool_triples_without_auth(monkeypatch):
    from pathlib import Path

    from databricks_agentkit.langgraph import genie_tools

    monkeypatch.setenv(
        "AGENTBRICKS_PROJECT_ROOT", str(Path(__file__).resolve().parents[1])
    )
    native = genie_tools()
    assert {t.name for t in native} == {
        f"{domain}_{method}"
        for domain in ("sales", "inventory")
        for method in ("ask", "poll", "query_result")
    }


def test_adapter_ignores_caller_selected_actor(monkeypatch):
    from runtime.adapter import _actor

    monkeypatch.setenv("DEMO_ACTOR_ID", "trusted-demo")
    assert _actor({"actor": "another-user"}, "session-a") == "trusted-demo"
    assert _actor({}, "session-b") == "trusted-demo"
