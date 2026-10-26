"""Record pipeline-readable messages separately from opaque LangGraph checkpoints."""

import asyncio
import hashlib
from typing import Any

from databricks.sdk.errors import AlreadyExists, ResourceAlreadyExists
from databricks_agentkit import AgentKitClient, workspace_client
from databricks_agentkit.runtime.tool_manifest import resolve_session_store


def transcript_session_id(actor: str, invocation_id: str) -> str:
    """Use a deterministic session per completed turn, grouping turns through actor_id."""
    digest = hashlib.sha256(f"{actor}\0{invocation_id}".encode()).hexdigest()
    return f"transcript-{digest}"


def message_items(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only text user/assistant messages in the documented distillation shape."""
    items = []
    for message in messages:
        role = message.get("role", message.get("type"))
        role = {"human": "user", "ai": "assistant"}.get(role, role)
        content = message.get("content")
        if (
            role in {"user", "assistant"}
            and isinstance(content, str)
            and content.strip()
        ):
            items.append({"type": "message", "role": role, "content": content})
    return items


def persist_turn(
    store: Any,
    actor: str,
    session_id: str,
    invocation_id: str,
    messages: list[dict[str, Any]],
) -> None:
    """Append a turn once on ordinary retries, validating ownership and existing content.

    Listing and appending are separate operations. This is not an exactly-once transaction;
    Runtime Store ordering handles normal execution, while crash windows are documented.
    """
    items = message_items(messages)
    if not items:
        return
    key = transcript_session_id(actor, invocation_id)
    try:
        session = store.add(
            actor_id=actor,
            session_id=key,
            metadata={
                "source_session_id": session_id,
                "invocation_id": invocation_id,
                "kind": "transcript",
            },
        )
    except (AlreadyExists, ResourceAlreadyExists):
        session = store.get(key)
    if session.actor_id != actor:
        raise PermissionError("Transcript belongs to a different actor")
    existing = [item.data for item in session.list_items(order_by="create_time asc")]
    if existing:
        if existing != items:
            raise ValueError(
                "Existing transcript differs; refusing to append a duplicate turn"
            )
        return
    session.append_items(items)


async def record_turn(
    actor: str, session_id: str, invocation_id: str, messages: list[dict[str, Any]]
) -> None:
    """Write to the bound store; perform no remote calls when no store is configured."""
    store_name = resolve_session_store(None)
    if not store_name:
        return

    def write() -> None:
        store = AgentKitClient(workspace_client()).session_stores.get(store_name)
        persist_turn(store, actor, session_id, invocation_id, messages)

    await asyncio.to_thread(write)
