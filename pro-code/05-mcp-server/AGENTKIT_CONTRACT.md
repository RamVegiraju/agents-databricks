# AgentKit integration contract

`app.yaml` starts `runtime.main:app`, which registers `invoke` and `recover` with `DurableAgentServer`. `runtime/adapter.py` accepts `POST /api/invocations` with a fresh invocation UUID, a top-level `session_id`, and `input.messages` containing role/content objects. It streams message and delta events, then returns `output` and `status`.

`agent/agent.py` loads the managed MCP tools declared in `agent.toml` through AgentKit's `mcp_tools()`. The LangGraph loop lets the model call those tools and incorporate the results. The App identity is used for the MCP binding and model calls; the service must grant that identity access.

This sample declares no Session Store. The checkpointer uses process memory, so conversation history can disappear after a restart or request routing to another instance. A deployed Runtime Store persists invocation state. Recovery replays the original input if the process has no matching checkpoint; do not add non-idempotent tools without handling replay.
