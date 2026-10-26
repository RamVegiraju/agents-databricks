"""Small diagnostic route for the horizontal scaling walkthrough."""

from uuid import uuid4

from databricks_agentkit import DurableAgentServer

# Generated once per server process. It is only an observation aid, never session state.
_REPLICA_ID = str(uuid4())


def install_replica_route(app: DurableAgentServer) -> None:
    @app.get("/api/replica")
    async def replica() -> dict[str, str]:
        return {"replica_id": _REPLICA_ID}
