"""Compose the released AgentKit memory tools and optional pre-run retrieval."""

import asyncio
import os

from databricks_agentkit import AgentKitClient, workspace_client
from databricks_agentkit.langgraph import memory_tools
from databricks_agentkit.runtime.tool_manifest import resolve_memory_store
from langchain_core.tools import BaseTool


def selected_memory_tools(actor: str) -> list[BaseTool]:
    """Return four tools, or only recall/list when pipeline extraction owns writes."""
    if not actor:
        raise ValueError("A trusted actor is required")
    mode = os.getenv("MEMORY_WRITE_MODE", "tools")
    if mode not in {"tools", "pipeline"}:
        raise ValueError("MEMORY_WRITE_MODE must be tools or pipeline")
    tools = memory_tools(actor)
    return (
        tools
        if mode == "tools"
        else [t for t in tools if t.name in {"recall", "list_memories"}]
    )


async def recalled_context(actor: str, query: str) -> str:
    """Optionally recall before the model runs, without writing facts into graph state."""
    store_id = resolve_memory_store(None)
    if (
        os.getenv("MEMORY_AUTO_RECALL", "false").lower() != "true"
        or not query
        or not store_id
    ):
        return ""

    def search() -> str:
        store = AgentKitClient(workspace_client()).memory_stores.get(store_id)
        return "\n".join(
            f"{result.memory.path}: {result.memory.content}"
            for result in store.search(actor_id=actor, query=query, limit=5)
        )

    return await asyncio.to_thread(search)
