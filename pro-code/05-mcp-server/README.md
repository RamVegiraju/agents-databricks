# 05 · MCP tools

Connect a LangGraph agent to the Databricks-managed `system.ai.web_search` MCP service.
AgentKit discovers the service's tools and makes them available to the model. This sample is an
MCP **client**, not a custom MCP server; no third-party account or token is required.

## Before you start

Complete the [shared setup](../../docs/GETTING_STARTED.md). Your workspace must expose
`system.ai.web_search` and permit the App identity to use it.

```bash
cd pro-code/05-mcp-server
export PROFILE="my-workspace"
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen pytest -q
uv run --frozen agentbricks --profile "$PROFILE" tools list --kind mcp
```

The service is already bound in `agent.toml`. If unavailable, choose a supported service and update
that binding and the prompt before deploying.

## Run

```bash
export AGENT_NAME="mcp-research"
export APP_NAME="agent-bricks-$AGENT_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source .
uv run --frozen agentbricks --profile "$PROFILE" endpoint invoke "$APP_NAME" \
  --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"research-demo\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Search the web for the latest LangGraph release notes. Summarize two changes and cite the source URLs.\"}]},\"stream\":false}"
```

## Inspect the result

Look for a successful web-search tool call/result followed by a cited answer. A citation alone does
not prove that the tool ran. Use a fresh invocation UUID for each request. This sample has no chat
UI or managed conversation store; its deployed Runtime Store preserves invocation records.

```bash
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "$APP_NAME" --yes
```

## Customize

| File | Purpose / what to change |
| --- | --- |
| [agent.toml](agent.toml) | Managed MCP service binding and App authentication. |
| [agent/agent.py](agent/agent.py) | Prompt, model, `mcp_tools()` discovery, and tool execution. |
| [runtime/adapter.py](runtime/adapter.py), [runtime/main.py](runtime/main.py) | Invocation translation and server startup. |
| [app.yaml](app.yaml) | Startup and deployment-generated environment settings. |
| [tests/test_agent.py](tests/test_agent.py) | Offline graph/tool checks. |
| [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Dependencies and generated lockfile. |

In a new project, bind a service with `agentbricks tools add mcp SERVICE --name NAME --auth app`.
Keep the discovered tools connected to both the model and executor.
See [MCP documentation](https://docs.databricks.com/aws/en/agents/mcp-tools/) and
[AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md).
