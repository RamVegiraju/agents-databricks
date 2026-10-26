# Agent development guide

This sample is a CLI-first LangGraph agent served by `DurableAgentServer`. Read [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) before changing HTTP integration. The [README](README.md) has the local and deployment commands.

| Concern | File |
| --- | --- |
| Model, graph, tracing | `agent/agent.py` |
| Local clock tool | `agent/tools/sample_tool.py` |
| Invocation translation | `runtime/adapter.py` |
| Server startup | `runtime/main.py`, `app.yaml` |

For Agent Bricks CLI work, read [.agents/skills/agent-bricks-workflow/SKILL.md](.agents/skills/agent-bricks-workflow/SKILL.md) and inspect the installed CLI help. Run `uv run --frozen agentbricks doctor .` and `uv run --frozen pytest -q` after integration changes.
