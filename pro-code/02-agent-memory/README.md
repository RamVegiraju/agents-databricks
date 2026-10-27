# 02 · Agent memory

This LangGraph agent shows two kinds of state on Databricks Apps: a **Session Store** keeps conversation history within a session, and a **Memory Store** keeps actor-scoped facts across sessions. The agent has one local UTC clock tool and the AgentKit `remember`, `recall`, `list_memories`, and `forget` tools. Its App also has a Runtime Store for durable invocation records. The browser chat at the deployed App URL shows sessions and memory.

## Deploy

Choose a Databricks CLI profile for a workspace with Apps, managed stores, an MLflow experiment, and access to `system.ai.claude-sonnet-4-5` (or change `MODEL` in `agent/agent.py`). From the repository root:

```bash
cd pro-code/02-agent-memory
databricks auth profiles
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> deploy <unique-name> --source .
databricks apps get agent-bricks-<unique-name> --profile <profile>
```

Open the App URL from `apps get` for the browser demo. The CLI deploy creates or reuses the stores and tracing experiment declared in `agent.toml`. Find the App under **Compute → Apps**. Reusing `<unique-name>` updates that App.

## Demonstrate memory in two sessions

Run each command from `pro-code/02-agent-memory`. Replace `<unique-name>` and `<profile>`. Use a new invocation UUID for each request; the example IDs below are distinct. The server uses one fixed `DEMO_ACTOR_ID` for this single-user demo, so both sessions see the same actor's Memory Store. Request payloads cannot choose another actor.

```bash
uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"11111111-1111-4111-8111-111111111111","session_id":"memory-demo-a","input":{"messages":[{"role":"user","content":"Remember this test preference: I prefer concise Python examples. Save it under the preferences topic and confirm only after the remember tool succeeds."}]},"stream":false}'

uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"22222222-2222-4222-8222-222222222222","session_id":"memory-demo-b","input":{"messages":[{"role":"user","content":"Use the recall tool to find my saved preference for Python examples. What does it say?"}]},"stream":false}'

uv run --frozen agentbricks --profile <profile> endpoint invoke agent-bricks-<unique-name> \
  --path /api/invocations \
  --json '{"id":"33333333-3333-4333-8333-333333333333","session_id":"memory-demo-b","input":{"messages":[{"role":"user","content":"Forget the fact that I prefer concise Python examples from the preferences topic. Confirm only after the forget tool succeeds, then use list_memories to show what is still stored."}]},"stream":false}'
```

The first turn writes a fact in session A. The second recalls it in session B, proving the fact is available across conversations. The third removes it from the Memory Store. Session B still retains its conversation history; forgetting a memory does not erase prior messages. For a clean final recall check, start a new session and use a new invocation UUID.

`agentbricks dev` is useful for local code iteration, but its conversation state is process-local and managed long-term memory is disabled. Run this memory demonstration against a deployed App. For the code walkthrough, show `agent.toml` (store bindings), `agent/agent.py` (graph and tool wiring), `agent/memory.py` (actor-scoped memory tools), `runtime/adapter.py` (trusted demo actor and session mapping), and `runtime/main.py` (durable server). See [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) for the request and recovery contract.

Run offline checks with `uv run --frozen pytest -q`. CLI commands and integration follow Agent Bricks 0.7.0, the [CLI documentation](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli), and the [Agent Bricks source](https://github.com/databricks/databricks-ai-bridge/tree/main/integrations/agentbricks/src).
