# Agent development guide

Read [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) before changing HTTP or recovery wiring. The [README](README.md) has the deployment and invocation flow. `agent.toml` owns the MCP binding; `agent/agent.py` builds the LangGraph tool loop; `runtime/adapter.py` maps Agent Bricks invocations to that graph.

Inspect the installed Agent Bricks CLI help for command syntax. Run `uv run --frozen agentbricks doctor .` after integration changes. Do not commit workspace IDs, profile names, tokens, or generated deployment settings.
