# 05 · MCP web research agent

This LangGraph agent uses the Databricks-managed `system.ai.web_search` MCP service. AgentKit reads the binding in `agent.toml`, discovers its tools for each invocation, and offers them to the model. No third-party MCP account or token is required. Your workspace must expose the service and allow the App identity to use it.

## Repository structure and adaptation

Focus on the declarative managed-MCP binding and how discovered tools reach both the model and executor. This sample consumes an existing MCP service; it does not implement an MCP server. To adapt it, choose an available service, match the prompt to its tools, and verify actual tool execution.

| File or directory | Role in this demo | Adapt for your own agent |
| --- | --- | --- |
| [agent.toml](agent.toml) | Binds system.ai.web_search as web_search with App identity. | Select your service, binding name, and supported auth model; verify workspace availability. |
| [agent/agent.py](agent/agent.py) | Model/prompt, mcp_tools() discovery, and the LangGraph tool loop. | Change task instructions/model; preserve discovery into both tool binding and execution. |
| [runtime/adapter.py](runtime/adapter.py) | Invocation input/output translation and recovery. | Change only for a new client contract or identity requirements. |
| [runtime/main.py](runtime/main.py) | Starts DurableAgentServer. | Usually retain. |
| [app.yaml](app.yaml) | Server startup command and deployment-generated settings. | Set application environment; regenerate workspace-specific deployment values rather than copying them. |
| [pyproject.toml](pyproject.toml) | AgentKit, LangGraph, and MCP dependencies. | Manage additional dependencies here. |
| [uv.lock](uv.lock) | Generated dependency lockfile for local commands. | Regenerate with uv after intentional dependency changes. |
| [tests/test_agent.py](tests/test_agent.py) | Offline graph/tool/runtime checks. | Add representative service-result, tool-error, and output-evidence cases. |
| [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) | HTTP and durable invocation integration contract. | Consult before changing server integration. |

## Run

Choose a Databricks CLI profile and a unique deployment name.
If needed, create the profile with `databricks auth login --host <workspace-url> --profile <profile>`.
From the repository root:

```bash
cd pro-code/05-mcp-server
databricks auth profiles
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> tools list --kind mcp
uv run --frozen agentbricks --profile <profile> deploy <unique-name> --source .
databricks apps get agent-bricks-<unique-name> --profile <profile>
```

`agent.toml` already binds `system.ai.web_search` with App identity. If `tools list` does not show that service in your workspace, choose an available managed MCP service and update the binding and prompt before deploying. To demonstrate how the CLI adds this service in a fresh project, run `uv run --frozen agentbricks --profile <profile> tools add mcp system.ai.web_search --name web_search --auth app` there. Do not repeat that command in this checked-in directory; the binding already exists.

Invoke the deployed agent with a fresh UUID:

```bash
uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"11111111-1111-4111-8111-111111111111","session_id":"research-1","input":{"messages":[{"role":"user","content":"Search the web for the latest LangGraph release notes. Summarize two changes and cite the source URLs."}]},"stream":false}'
```

Check the response events for a `web_search` tool call and its result; a cited answer alone does not prove MCP ran. Use a new `id` for each call. The sample has no managed Session Store, so conversation state is local to the process; Agent Bricks still provisions its Runtime Store for invocation records.

For the video, show `agent.toml` (MCP binding), `agent/agent.py` (`mcp_tools()` and LangGraph tool loop), `runtime/adapter.py` (invocation translation), and `app.yaml` (start command). [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) describes the HTTP and recovery contract.

Validated against Agent Bricks CLI 0.7.0 and its installed `tools add mcp` help, the [Agent Bricks CLI docs](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli), and [MCP docs](https://docs.databricks.com/aws/en/agents/mcp-tools/). A deployed invocation returned a `web_search` tool call and successful result; search content changes over time.
