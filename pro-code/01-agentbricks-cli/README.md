# 01 · Agent Bricks CLI quickstart

The Agent Bricks CLI starts a new LangGraph project with:

```bash
uvx --from databricks-agentbricks==0.6.0 agentbricks init --framework langgraph my-agent
```

That command creates a separate `my-agent/` scaffold. The end-to-end commands below run the
checked-in, smaller sample in `pro-code/01-agentbricks-cli/`: a LangGraph agent with one local
`get_current_time` tool. It needs no configured Session Store, Memory Store, or external tool;
deployment still uses Agent Bricks' Runtime Store for invocation records.

## Run locally

Choose a Databricks CLI profile for a workspace with access to `system.ai.claude-sonnet-4-5` (or change `MODEL` in `agent/agent.py`):

```bash
cd pro-code/01-agentbricks-cli
databricks auth profiles
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> dev
```

In another terminal, invoke the local agent:

```bash
uv run --frozen agentbricks --profile <profile> endpoint invoke \
  --url http://localhost:8000 --path /api/invocations \
  --json '{"id":"11111111-1111-4111-8111-111111111111","session_id":"demo-1","input":{"messages":[{"role":"user","content":"Use your tool to tell me the UTC time."}]},"stream":false}'
```

Use a new `id` for each invocation. Local `dev` uses process memory for conversation state and invokes the chosen workspace model.

## Deploy

```bash
uv run --frozen agentbricks --profile <profile> deploy <unique-name> --source .
databricks apps get agent-bricks-<unique-name> --profile <profile>
uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"22222222-2222-4222-8222-222222222222","session_id":"demo-2","input":{"messages":[{"role":"user","content":"Use your tool to tell me the UTC time."}]},"stream":false}'
```

`deploy` creates or updates the named Databricks App and returns its URL. The App uses its own
identity to call the model. Reusing `<unique-name>` updates that App.

For a code walkthrough, show `agent.toml` (project settings), `app.yaml` (start command), `agent/agent.py` (graph and model), `agent/tools/sample_tool.py` (local tool), and `runtime/main.py` (HTTP server). `runtime/adapter.py` translates Agent Bricks invocations into LangGraph messages. The HTTP request contract is in [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md).

Run offline checks with `uv run --frozen pytest -q`.

Commands and runtime wiring were checked against Agent Bricks CLI 0.6.0, the
[CLI documentation](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli), and
the [Agent Bricks source](https://github.com/databricks/databricks-ai-bridge/tree/main/integrations/agentbricks/src).
