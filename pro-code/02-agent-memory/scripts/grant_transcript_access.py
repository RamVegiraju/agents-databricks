"""Grant the deployed App access to its separate readable-transcript store.

Run once after deployment: uv run --frozen python scripts/grant_transcript_access.py
--profile PROFILE --app APP --store STORE. Requires permission to grant store access.
The CLI manages checkpoint/memory grants; this explicit SDK call covers the extra store.
"""

import argparse

from databricks.sdk import WorkspaceClient
from databricks_agentkit import AgentKitClient


def main() -> None:
    """Resolve the actual App principal and grant access through the public SDK."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--store", required=True)
    args = parser.parse_args()
    workspace = WorkspaceClient(profile=args.profile)
    principal = workspace.apps.get(args.app).service_principal_client_id
    if not principal:
        raise ValueError("App has no service principal client ID")
    AgentKitClient(workspace).session_stores.get(args.store).grant_permission(principal)
    print(f"Granted {args.app} access to {args.store}")


if __name__ == "__main__":
    main()
