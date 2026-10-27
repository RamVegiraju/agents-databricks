# 05 · MCP web research agent

This LangGraph agent uses the Databricks-managed `system.ai.web_search` MCP service. AgentKit reads the binding in `agent.toml`, discovers its tools for each invocation, and offers them to the model. No third-party MCP account or token is required. Your workspace must expose the service and allow the App identity to use it.

## Run

Choose a Databricks CLI profile and a unique deployment name:

```bash
cd pro-code/05-mcp-server
databricks auth profiles
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> tools list --kind mcp
uv run --frozen agentbricks --profile <profile> deploy <unique-name> --source .
databricks apps get agent-bricks-<unique-name> --profile <profile>
```

`agent.toml` already binds `system.ai.web_search` with App identity. To demonstrate how the CLI adds a managed MCP service in a fresh project, run `agentbricks --profile <profile> tools add mcp system.ai.web_search --name web_search --auth app` there. Do not repeat that command in this checked-in directory; the binding already exists.

Invoke the deployed agent with a fresh UUID:

```bash
uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"11111111-1111-4111-8111-111111111111","session_id":"research-1","input":{"messages":[{"role":"user","content":"Search the web for the latest LangGraph release notes. Summarize two changes and cite the source URLs."}]},"stream":false}'
```

Check the response events for a `web_search` tool call and its result; a cited answer alone does not prove MCP ran. Use a new `id` for each call. The sample has no managed Session Store, so conversation state is local to the process; Agent Bricks still provisions its Runtime Store for invocation records.

For the video, show `agent.toml` (MCP binding), `agent/agent.py` (`mcp_tools()` and LangGraph tool loop), `runtime/adapter.py` (invocation translation), and `app.yaml` (start command). [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) describes the HTTP and recovery contract.

Validated against Agent Bricks CLI 0.7.0 and its installed `tools add mcp` help, the [Agent Bricks CLI docs](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli), and [MCP docs](https://docs.databricks.com/aws/en/agents/mcp-tools/). A deployed invocation returned a `web_search` tool call and successful result; search content changes over time.
