"""Chunk local policies and MERGE into a CDF-enabled Delta source table.

Default mode prints the plan; --apply is required before resolving workspace auth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    ExecuteStatementRequestOnWaitTimeout,
    StatementParameterListItem,
    StatementState,
)

POLICY_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"


def sql_name(name: str) -> str:
    """Quote a fully qualified identifier, rejecting SQL fragments."""
    if not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", name
    ):
        raise ValueError(
            "Expected catalog.schema.table using letters, numbers and underscores"
        )
    return ".".join(f"`{part}`" for part in name.split("."))


def policy_chunks(
    directory: Path = POLICY_DIR, chunk_size: int = 1200
) -> list[dict[str, str]]:
    """Produce stable source/offset IDs and portable citation URIs for small demo docs."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    chunks = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ")
        for offset in range(0, len(text), chunk_size):
            chunks.append(
                {
                    "chunk_id": hashlib.sha256(
                        f"{path.name}:{offset}".encode()
                    ).hexdigest(),
                    "content": text[offset : offset + chunk_size],
                    "source_uri": f"northstar-policy://{path.name}",
                    "title": title,
                }
            )
    return chunks


def execute(
    w: WorkspaceClient, warehouse_id: str, statement: str, **kwargs: Any
) -> None:
    """Require completion; cancel timeouts instead of submitting dependent SQL too soon."""
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="50s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CANCEL,
        **kwargs,
    )
    if not result.status or result.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"SQL did not succeed: {result.as_dict()}")


def ingest(
    w: WorkspaceClient, warehouse_id: str, table: str, chunks: list[dict[str, str]]
) -> None:
    """Create a dedicated source table and idempotently update its policy chunks."""
    target = sql_name(table)
    execute(
        w,
        warehouse_id,
        f"""CREATE TABLE IF NOT EXISTS {target}
        (chunk_id STRING, content STRING, source_uri STRING, title STRING)
        USING DELTA TBLPROPERTIES (delta.enableChangeDataFeed = true)""",
    )
    execute(
        w,
        warehouse_id,
        f"ALTER TABLE {target} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)",
    )
    for chunk in chunks:
        execute(
            w,
            warehouse_id,
            f"""MERGE INTO {target} t
            USING (SELECT :chunk_id AS chunk_id, :content AS content,
                          :source_uri AS source_uri, :title AS title) s
            ON t.chunk_id = s.chunk_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *""",
            parameters=[
                StatementParameterListItem(name=k, value=v, type="STRING")
                for k, v in chunk.items()
            ],
        )


def main() -> None:
    """Preview or explicitly apply ingestion; never run on application startup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--warehouse-id")
    parser.add_argument("--table", default="northstar_demo.retail.policy_chunks")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sql_name(args.table)
    chunks = policy_chunks()
    if not args.apply:
        print(
            json.dumps(
                {"mode": "preview", "table": args.table, "chunks": chunks}, indent=2
            )
        )
        return
    if not args.profile or not args.warehouse_id:
        parser.error("--apply requires --profile and --warehouse-id")
    ingest(WorkspaceClient(profile=args.profile), args.warehouse_id, args.table, chunks)
    print(f"Merged {len(chunks)} chunks into {args.table}")


if __name__ == "__main__":
    main()
