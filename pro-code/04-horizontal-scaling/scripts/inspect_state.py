"""Read existing managed memory/session state without creating resources."""

import argparse
import json

from databricks.sdk import WorkspaceClient
from databricks_agentkit import AgentKitClient


def main() -> None:
    """Read one actor through the public AgentKit resource APIs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--memory-store", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--query")
    parser.add_argument("--session-store")
    parser.add_argument("--session")
    args = parser.parse_args()
    if bool(args.session_store) != bool(args.session):
        parser.error("--session-store and --session must be supplied together")
    client = AgentKitClient(WorkspaceClient(profile=args.profile))
    store = client.memory_stores.get(args.memory_store)
    memories = (
        [
            r.memory
            for r in store.search(actor_id=args.actor, query=args.query, limit=10)
        ]
        if args.query
        else list(store.list(actor_id=args.actor))
    )
    output = {
        "memories": [
            {"path": m.path, "content": m.content, "session_id": m.session_id}
            for m in memories
        ]
    }
    if args.session:
        session = client.session_stores.get(args.session_store).get(args.session)
        if session.actor_id != args.actor:
            raise PermissionError("Session belongs to another actor")
        output["session_items"] = [
            item.data for item in session.list_items(order_by="create_time asc")
        ]
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
