# 01 · Agent Bricks CLI quickstart

Run a LangGraph agent with a Python clock tool, then deploy it to Databricks Apps.
This sample is API-only: it has no chat UI or managed conversation/memory stores.

## Before you start

Complete the [shared setup](../../docs/GETTING_STARTED.md). You need access to
`system.ai.claude-sonnet-4-5`, or change the model in `agent/agent.py`.

```bash
cd pro-code/01-agentbricks-cli
export PROFILE="my-workspace"
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen pytest -q
```

## Run locally

In terminal 1:

```bash
uv run --frozen agentbricks --profile "$PROFILE" dev
```

In terminal 2, from the same directory:

```bash
export PROFILE="my-workspace"
uv run --frozen agentbricks --profile "$PROFILE" endpoint invoke \
  --url http://localhost:8000 --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"clock-demo\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Use your tool to tell me the UTC time.\"}]},\"stream\":false}"
```

Check for `completed`, a successful `get_current_time` tool result, and an answer using its timestamp.
Stop the local server with Ctrl+C. Conversation state is lost when the process stops.

## Deploy

```bash
export AGENT_NAME="cli-quickstart"
export APP_NAME="agent-bricks-$AGENT_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source .
uv run --frozen agentbricks --profile "$PROFILE" endpoint invoke "$APP_NAME" \
  --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"clock-deployed\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Use your tool to tell me the UTC time.\"}]},\"stream\":false}"
```

The deployed Runtime Store preserves invocation records; conversation checkpoints remain in process memory.
Stop compute after testing:

```bash
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "$APP_NAME" --yes
```

## Customize

| File | Purpose / what to change |
| --- | --- |
| [agent/agent.py](agent/agent.py) | Model, prompt, and model → tool → model loop. |
| [agent/tools/sample_tool.py](agent/tools/sample_tool.py) | Replace the clock with a domain tool. |
| [agent/tools/__init__.py](agent/tools/__init__.py) | Local tool discovery. |
| [agent.toml](agent.toml), [app.yaml](app.yaml) | Bindings and startup; deploy generates workspace settings. |
| [runtime/adapter.py](runtime/adapter.py), [runtime/main.py](runtime/main.py) | Invocation translation and server startup. |
| [tests/](tests/) | Offline graph and route checks. |
| [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Dependencies and generated lockfile. |

To scaffold a separate project instead, run `uvx --from databricks-agentbricks==0.7.0 agentbricks init --framework langgraph my-agent` in an unused directory. The default template includes a UI and session/memory bindings; this smaller sample does not.

Next: [Agent memory](../02-agent-memory/README.md). For runtime changes, read [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md).
