"""AI Search retrieval using the Workspace SDK (the SDK retains vector_search naming)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks_agentkit import workspace_client
from langchain_core.tools import BaseTool, tool


def decode_hits(response: Any) -> list[dict[str, Any]]:
    """Decode named result columns rather than assuming score/column positions."""
    payload = response.as_dict()
    columns = [
        column["name"] for column in payload.get("manifest", {}).get("columns", [])
    ]
    rows = payload.get("result", {}).get("data_array", [])
    if rows and not columns:
        raise ValueError("AI Search returned rows without a column manifest")
    return [dict(zip(columns, row, strict=True)) for row in rows]


def build_policy_tools(
    *,
    client_factory: Callable[[], WorkspaceClient] = workspace_client,
    index_name: str | None = None,
) -> list[BaseTool]:
    """Build an async tool; do not resolve auth or call the workspace at import time."""
    bound_index = index_name or os.getenv("POLICY_INDEX_NAME")

    @tool
    async def search_policies(query: str) -> dict[str, Any]:
        """Retrieve Northstar return, shipping or replenishment policies with citations."""
        if not query.strip():
            raise ValueError("query must not be blank")
        if not bound_index:
            raise ValueError("Set POLICY_INDEX_NAME to an existing AI Search index")

        def fetch() -> Any:
            return client_factory().vector_search_indexes.query_index(
                index_name=bound_index,
                query_text=query,
                query_type="HYBRID",
                columns=["chunk_id", "content", "source_uri", "title"],
                num_results=4,
            )

        hits = decode_hits(await asyncio.to_thread(fetch))
        return {"index": bound_index, "matches": hits}

    return [search_policies]
