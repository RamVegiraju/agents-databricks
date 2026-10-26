# 01 · Hello World with managed memory

An explicit LangGraph model/tool loop with one local UTC clock tool, browser chat, and the current
AgentKit memory/session integrations.

```text
Browser → DurableAgentServer → runtime/adapter.py → LangGraph agent ↔ tools → END
Session Store: graph checkpoints + separate pipeline-readable transcript sessions
Memory Store: remember / recall / list_memories / forget
Memory pipeline: transcripts → extraction → consolidation → Memory Store
```

## Install and validate offline

```bash
cd pro-code/01-hello-memory
uv sync --frozen --group dev
uv run --frozen pytest -q
uv run --frozen agentbricks doctor .
```

Integration versions: Agent Bricks 0.6.0, Databricks SDK 0.154.0, databricks-langchain 0.21.0.
The lock records resolved dependencies. Tests execute real LangGraph routing and released memory
tools with injected model/storage boundaries. Live tests require `RUN_LIVE_TESTS=true` explicitly.

## Basic local app

Choose a workspace/profile yourself. Nothing selects a workspace automatically:

```bash
databricks auth profiles
databricks auth login --host https://<workspace-host> --profile <profile>
uv run agentbricks --profile <profile> dev
```

Open http://localhost:8000 and ask “Use your tool to tell me the UTC time.” The generated default
model is `system.ai.claude-sonnet-4-5`. Its availability is unverified: choose a model your workspace
exposes in the UI or edit MODEL in agent/agent.py.

**Dev mode is local:** CLI 0.6.0 `dev --help` says it disables long-term memory and uses in-process
conversation state despite bindings. It calls workspace model/tool services. A dev response does
not prove managed-memory persistence.

## Managed memory locally, without deployment

These optional commands create workspace resources when you run them.
Choose unique names and edit the bindings if these example names already belong to another project.

```bash
uv run agentbricks --profile <profile> sessions stores create --name hello-memory-demo-sessions
uv run agentbricks --profile <profile> --output json memory stores create --display-name hello-memory-demo-memory
uv run agentbricks sessions bind hello-memory-demo-sessions
uv run agentbricks memory bind hello-memory-demo-memory
```

Keep the returned memory store ID/resource name. Do not infer an opaque ID from its display name.
Copy `.env.example` to `.env`, set your profile and the actual existing store identifiers, then run:

```bash
uv run start-server
```

This bypasses dev's local-state overrides. It runs the same app entrypoint against existing managed
stores using your local credentials, without provisioning. Model calls and state writes are live.
Invocation execution remains process-local; this does not establish deployed Runtime Store durability.
Memory/checkpoints persist only if the configured stores exist and your identity can access them.

## Identity and request contract

This introductory sample is a **single-user sandbox**. The server chooses `DEMO_ACTOR_ID` (default
`agent`), which stays stable across chats. The adapter ignores caller-supplied `input.actor`, and
memory UI routes ignore arbitrary actor overrides. Use a fresh conversation UUID per chat and a
fresh invocation UUID per turn. The browser handles these values.

POST `/api/invocations` with this body (replace IDs for each appropriate scope):

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "session_id": "chat-A",
  "input": {"messages": [{"role": "user", "content": "Remember that I prefer Python."}]},
  "background": false,
  "stream": false
}
```

Use `stream: true` for SSE or `background: true` for polling. AgentKit handles scheduling and
heartbeats; the application only awaits model execution and offloads synchronous SDK I/O.

Actors are grouping keys, not access controls. The released saver resolves sessions by thread ID,
so never reuse a session ID across actors. Before production multi-user use, derive trusted identity,
namespace conversation IDs and enforce ownership on every session/history route. Separate store
pairs are required for strict tenant isolation. No production multi-user authentication is claimed.

## Memory walkthrough

| Feature | Action | Evidence to inspect |
| --- | --- | --- |
| Local tool | “Use your tool to tell me the UTC time.” | Clock tool call and result |
| Session state | “For this chat only, my color is teal.” Then ask its color in the same chat | Checkpointed history |
| Explicit write | “Remember that I prefer Python.” | Successful remember result |
| Cross-chat recall | New chat: “What language do I prefer? Use recall.” | Same actor, new session, recall result |
| Inspect | “List your saved memories.” | list_memories paths and facts |
| Correct | “Forget the old language preference and remember that I prefer Rust.” | forget and remember results |
| Forget | “Forget that I prefer Rust.” | Exact fact removed; search confirms |
| Automatic retrieval | Set MEMORY_AUTO_RECALL=true and restart | Relevant memory injected before the model call |
| Pipeline-only writes | Set MEMORY_WRITE_MODE=pipeline and restart | Only recall/list tools available; pipeline writes later |

The four memory tools come from the released AgentKit adapter. Forget matches normalized fact
lines; inspect the exact stored wording and path first. Model behavior and extraction quality need
live checks; offline tests validate wiring, not model quality or service availability.

Forgetting a memory does not erase its source transcript/checkpoints. A later pipeline can extract
it again. Full erasure requires a separate retention/deletion workflow. The released memory append
and forget paths use read/modify/write, so concurrent writers can lose updates.

## Memory pipeline and transcript

LangGraph checkpoints are opaque to memory pipelines. `agent/transcript.py` additionally records
completed text user/assistant turns in the documented type=message shape. Tool results/system
prompts are excluded. Each invocation gets a deterministic transcript session with metadata linking
its source chat. Its actor matches the memory actor, so the pipeline can combine turns across chats.

Ordinary retries compare existing transcript content and skip duplicate appends. Graph state,
Runtime Store events and transcript writes are not one transaction. A crash after graph completion
but before transcript persistence requires recovery/reconciliation; concurrent recorder execution
is not an exactly-once guarantee. Only completed text turns are distilled by this recorder.

These optional commands create/run serverless and model work and can incur charges:

```bash
uv run agentbricks --profile <profile> memory pipeline create \
  --session-store hello-memory-demo-sessions \
  --memory-store <memory-store-id-or-resource-name> \
  --trigger manual \
  --instructions @resources/memory-instructions.txt
uv run agentbricks --profile <profile> memory pipeline run <pipeline-id>
uv run agentbricks --profile <profile> memory pipeline get <pipeline-id>
uv run agentbricks --profile <profile> memory pipeline update <pipeline-id> --trigger scheduled
```

Scheduled means approximately every 24 hours; no configurable interval/cron. Only one run can be
active. The default distillation model is service-selected; pass --model with an accessible model
service if needed. The pipeline may reorganize entries that tools wrote directly. Check run results:

```bash
databricks --profile <profile> api get /api/2.0/agents/memory-pipelines/<pipeline-id>/runs/<run-id>
```

The 0.6.0 CLI has pipeline configuration get, not a dedicated run-result get command.

## CLI and SDK inspection

```bash
uv run agentbricks --profile <profile> memory entries list --store <memory-store-id> --actor-id agent
uv run agentbricks --profile <profile> memory entries search --store <memory-store-id> --actor-id agent --query Python
uv run agentbricks --profile <profile> sessions list --store hello-memory-demo-sessions
uv run agentbricks --profile <profile> sessions items list --store hello-memory-demo-sessions --session-id <stored-session-id> --order-by 'create_time asc'
uv run python scripts/inspect_state.py --profile <profile> --memory-store <id> --actor agent --query Python
```

Entry create/get/update/delete are under memory entries; session fork and item pop/clear are under
sessions. Inspect --help before destructive operations. Forking Session Store checkpoint blobs is
not presented as validated LangGraph state forking. Use framework state-history APIs for graph forks.
The inspection script uses public AgentKit APIs and checks session ownership before returning items.

## Deployment path for later

When deployment is authorized, from this directory:

```bash
uv run agentbricks --profile <profile> deploy hello-memory-demo --source .
```

The CLI reads agent.toml, reconciles stores/access, configures tracing and supplies the deployment
Runtime Store. The memory pipeline is separately managed and runs using its creator's identity.
No setup is invoked by tests or app startup.

## Code and verification

- agent/agent.py: explicit graph, model, instructions, checkpoint/recovery integration.
- agent/memory.py: four tools, pipeline-only mode, optional pre-run recall outside graph state.
- agent/transcript.py: plain-message recording for distillation.
- runtime/adapter.py: invocation translation, fixed demo actor, transcript integration.
- agent.toml: declarative bindings; their presence does not prove a resource exists.

Checked against installed AgentKit0.6.0 langgraph/memory.py, langgraph/session_store.py,
resource session_store.py/memory_store.py and CLI memory/pipeline/sessions source/help.
Pipeline extraction and conversation continuity after worker loss remain unverified.

References:
[LangGraph](https://docs.langchain.com/oss/python/langgraph/quickstart),
[session/memory tutorial and transcript requirement](https://docs.databricks.com/aws/en/agents/agent-memory/existing-agent-tutorial),
[memory](https://docs.databricks.com/aws/en/agents/agent-memory/managed-memory),
[pipelines](https://docs.databricks.com/aws/en/agents/agent-memory/memory-pipelines),
[Agent Server](https://docs.databricks.com/aws/en/agents/deploy/agent-server),
[source](https://github.com/databricks/databricks-ai-bridge/tree/main/integrations/agentbricks).
