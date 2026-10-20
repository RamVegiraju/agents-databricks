"""Register GitHub's read-only remote MCP using a schema-level UC HTTP connection.

Preview is offline. --apply requires an explicit workspace profile and a real
MCP_SERVER_TOKEN. The token is only read in apply mode and is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import re

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog as c


def registration(schema: str, connection_name: str, service_name: str) -> dict:
    """Generate non-secret resource configuration from validated identifiers."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", schema):
        raise ValueError(
            "schema must be catalog.schema using lowercase letters/numbers/underscores"
        )
    for name in (connection_name, service_name):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError(
                "resource names must use lowercase letters/numbers/underscores"
            )
    return {
        "parent": f"schemas/{schema}",
        "connection_name": connection_name,
        "connection_options": {
            "host": "https://api.githubcopilot.com",
            "port": "443",
            "base_path": "/mcp/readonly",
        },
        "mcp_service_id": service_name,
        "mcp_service": c.McpService(
            comment="Northstar engineering repository lookup (read-only GitHub MCP)",
            config=c.McpServiceConfig(
                source_connection=c.McpServiceConfigSourceConnection(
                    name=f"connections/{schema}.{connection_name}",
                ),
                include_tool_selectors=["get_file_contents", "search_code"],
            ),
        ).as_dict(),
    }


def apply_registration(w: WorkspaceClient, plan: dict, token: str) -> None:
    """Create resources explicitly. Existing resources fail rather than being overwritten."""
    if not token.strip():
        raise ValueError("A real GitHub bearer token is required")
    w.connections.create(
        name=plan["connection_name"],
        parent=plan["parent"],
        connection_type=c.ConnectionType.HTTP,
        options={**plan["connection_options"], "bearer_token": token},
    )
    w.ai_gateway.create_mcp_service(
        parent=plan["parent"],
        mcp_service_id=plan["mcp_service_id"],
        mcp_service=c.McpService.from_dict(plan["mcp_service"]),
    )


def main() -> None:
    """Print an offline plan or explicitly register after --apply."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--schema", default="northstar_demo.retail")
    parser.add_argument("--connection", default="github_readonly")
    parser.add_argument("--service", default="github_docs")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = registration(args.schema, args.connection, args.service)
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return
    token = os.getenv("MCP_SERVER_TOKEN")
    if not args.profile or not token:
        parser.error("--apply requires --profile and MCP_SERVER_TOKEN")
    apply_registration(WorkspaceClient(profile=args.profile), plan, token)
    full_name = f"{args.schema}.{args.service}"
    print(f"Registered {full_name}; MCP URL: /ai-gateway/mcp-services/{full_name}")


if __name__ == "__main__":
    main()
