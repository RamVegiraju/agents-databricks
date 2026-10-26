# AgentKit integration contract

`app.yaml` starts `runtime.main:app`, which registers `invoke` and `recover` with `DurableAgentServer`. `runtime/adapter.py` accepts `POST /api/invocations` with a fresh invocation UUID, a stable top-level `session_id`, and `input.messages` containing LangChain-style role/content objects. The adapter streams message and delta events, then returns `output` and `status`.

The LangGraph loop and tool live in `agent/agent.py` and `agent/tools/sample_tool.py`. AgentKit's checkpointer uses process memory because this sample declares no Session Store. A deployed Runtime Store persists invocation records, but conversation history does not survive an App process restart or move between instances. Use a managed Session Store for durable multi-turn state. Recovery replays the original input if this process has no matching checkpoint, so external side effects would need replay-safe handling.

The default agent has no memory store, MCP server, browser UI, or user identity mapping. It is an introductory single-session example, not a multi-user application. `agentbricks dev` uses local state and local MLflow tracing; deployment uses the App's identity for model calls. Keep credentials out of source and pass a named CLI profile explicitly.
