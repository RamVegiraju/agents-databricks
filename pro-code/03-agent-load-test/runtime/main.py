"""Serve the inventory agent with the Agent Bricks durable runtime."""

import os

import uvicorn
from databricks_agentkit import DurableAgentServer
from databricks_agentkit.openai import configure_tracing

from agent.assistant import configure_client
from runtime.adapter import invoke, recover

configure_client()
configure_tracing()
app = DurableAgentServer()
app.invoke(invoke)
app.recover(recover)


if __name__ == "__main__":
    uvicorn.run("runtime.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
