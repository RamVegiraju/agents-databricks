# Memory demo validation · 2026-10-27

Validated in profile `ml-demos`, workspace `7474655512364318`, using the pinned Agent Bricks 0.7.0 environment. These observations are from live APIs, not inferred from configuration alone.

## Resources

| Resource | Observed identifier |
| --- | --- |
| App | [agent-bricks-agent-memory](https://agent-bricks-agent-memory-7474655512364318.aws.databricksapps.com) |
| Checkpoint Session Store | `agent-memory-demo-sessions` |
| Readable-transcript Session Store | `agent-memory-demo-transcripts` |
| Memory Store | `memory-stores/agent-memory-demo-memory` |
| Pipeline | `memory-pipelines/22fb18be-a9c3-402e-86a3-8d5d688386d9` |
| Successful manual run | `memory-pipelines/22fb18be-a9c3-402e-86a3-8d5d688386d9/runs/202573353185856` |
| Trusted demo actor | `agent` |
| Chat and distillation model | `system.ai.claude-sonnet-4-5` |
| Tracing experiment configured | `1263198253019603` |

Pipeline GET confirmed `dreamer_policy.enabled=true`, `trigger=SCHEDULED`, the selected model, and the exact contents of `resources/memory-instructions.txt`. A run on the daily schedule has not been observed yet; scheduling is verified as configured, while the on-demand asynchronous execution is verified end to end.

## Observed behavior

1. The Memory Store was empty before the demo conversations and remained empty before the manual pipeline run. The agent had only recall/list memory tools; no remember/forget writes occurred.
2. Session `cedar-final-a-20261027` received: “For project Cedar, I prefer concise Python examples. For this chat only, call the temporary test branch amber-42.”
3. A follow-up in that same session asked for both facts without repeating them. The agent answered “concise Python” and “amber-42” from session history, with no memory tool calls.
4. The separate transcript store held readable `{type: "message", role, content}` user and assistant items. Their metadata linked them to the original session/invocation.
5. After redeployment restarted the App, `/api/demo/session/items` reopened session A with both complete turns. This verifies restored history, separately from long-term memory.
6. The helper started one manual run and observed `RUNNING` followed by `SUCCEEDED`, with backing job termination `SUCCESS`. The source turn was older than the documented 60-second freshness cutoff.
7. Memory list returned two entries marked `MANAGED_MEMORY_ENTRY_SOURCE_TYPE_DREAMER`:
   - `projects/cedar.md`: “Use concise Python examples” under Project Cedar preferences.
   - `preferences/cedar.md`: “Prefers concise Python examples for Cedar code/documentation”.
8. Neither entry contained `amber-42`. These entries were session-scoped to their source transcript sessions. The first run did **not** consolidate the overlapping preference into a single entry; do not promise that result or an exact path.
9. Fresh session `cedar-final-b-20261027` called `recall` for the Cedar preference. The tool returned the two actual entries. A separate recall for a temporary test-branch name returned `No relevant memories.`
10. The agent applied the retrieved preference by returning a short Python duplicate-removal function, `return list(dict.fromkeys(strings))`, rather than only repeating the stored fact.

The test memories and conversations remain available for inspection. For a new rehearsal, choose another project and first inspect its baseline; the store is no longer empty.

## Run it again

From `pro-code/02-agent-memory`, after a new conversation completes and more than 60 seconds have passed:

```bash
uv run --frozen python scripts/pipeline_run.py --profile ml-demos \
  --pipeline memory-pipelines/22fb18be-a9c3-402e-86a3-8d5d688386d9

uv run --frozen agentbricks --profile ml-demos --output json memory entries list \
  --store agent-memory-demo-memory --actor-id agent
```

Only one run can be active. A monitoring timeout leaves the remote job running; use the helper's `--run <full-resource-name>` to continue monitoring it. The scheduled pipeline remains enabled for automatic runs about every 24 hours.

## Offline checks and scope

- `uv run --frozen pytest -q`: **61 passed, 1 skipped**, with one upstream Pydantic deprecation warning. The skipped test is the opt-in live smoke test; the deployed flow above was exercised separately.
- `uv run --frozen agentbricks doctor .`: **8/8 passed**.
- `git diff --check`: passed.
- Local-mode test verifies `agentbricks dev` cannot write to the managed transcript store even when custom app environment variables are retained.

This is a single-user capability demo. Multi-user identity integration, high-load performance, long-session context compaction, comprehensive retention/erasure, and benchmark quality/cost gains are not validated. The README documents concrete scale boundaries, including per-invocation transcript-session growth and current managed pipeline actor limits.

## Retrieval audit after the live demonstration

The latest offline checks additionally verify that automatic recall:

- Makes no workspace call when disabled, unconfigured, or given no query.
- Passes the trusted actor, incoming query, and five-entry limit to the configured store on each call.
- Handles an empty result without inventing context.

The released recall tool is also tested at the managed-store boundary for actor scope, query,
five-entry limit, and optional session filtering. These checks use fake store boundaries. They do
not validate the managed service's semantic ranking or the model's natural-language tool selection.
The existing graph test verifies supplied system context is not itself checkpointed as a message.

The original deployed pipeline acceptance run explicitly requested recall. The later natural-query
spot check below validates tool selection without that instruction. Automatic pre-run retrieval
still has not been live-validated. The configuration remains `MEMORY_AUTO_RECALL=false` and
`MEMORY_WRITE_MODE=pipeline`.

## Natural-language recall spot check · 2026-10-27

Started the existing App and verified its deployed source still had automatic recall off and
pipeline-only writes. Each case used a fresh session/invocation UUID. Existing memory held the two
pipeline-derived Cedar preference entries. No user prompt named the recall tool.

| Natural prompt | Observed tool behavior | Observed answer | Endpoint elapsed time |
| --- | --- | --- | --- |
| “What example style do I prefer for project Cedar?” | One recall call, query `project Cedar example style preference`. | Identified the saved concise-Python preference. | 20.42 s |
| “I'm writing project Cedar documentation. Show a function that removes duplicate strings, following my usual example style.” | Two recall calls with style/documentation queries. | Used the stored Python preference and supplied a working order-preserving deduplication example. | 25.45 s |
| “Which testing framework have I chosen for project Cedar?” | One recall call, query `project Cedar testing framework`. | Recognized that returned style entries did not establish a framework choice; asked for clarification. | 9.93 s |
| “What is 17 multiplied by 19? Just give the number.” | No tool calls. | Answered `323`. | 5.94 s |

The elapsed times include the endpoint invocation workflow and are not isolated model/search
latencies. The missing-fact search returned the existing Cedar style entries, rather than an empty
result; the model correctly distinguished their contents from the unanswered framework question.

MLflow trace `tr-123192d00774b312172c4b81c2da6b84` for the first case was `OK` and contained a
`recall` TOOL span between model calls. Actual prompts, generated queries, tool results, answers,
UUIDs, and the trace summary are in the [generated evidence](validation/natural-memory-2026-10-27.json).

All four spot checks showed the intended behavior. This is one run per prompt, one model, and a
small two-entry memory dataset. It does not establish statistical selection reliability, resistance
to unrelated distractors at scale, or guarantees for every model/input. No application-code/config
change or pipeline run was required. App compute was started for these tests and restored to its
original stopped state afterward. The schedule and persisted stores were left in place.

## Documentation and source cross-check

- [Stateful agent concepts](https://docs.databricks.com/aws/en/agents/custom-agents/stateful-agents): session state vs durable knowledge and episodic vs derived memory.
- [Existing-agent tutorial](https://docs.databricks.com/aws/en/agents/agent-memory/existing-agent-tutorial): separate readable transcripts for LangGraph, App store grants, and 60-second freshness cutoff.
- [Pipeline reference](https://docs.databricks.com/aws/en/agents/agent-memory/memory-pipelines): scheduled/manual triggers, asynchronous states, identity, and limitations.
- [Launch blog](https://www.databricks.com/blog/introducing-agent-memory-databricks) and [MemCurrent research](https://www.databricks.com/blog/memcurrent-designing-persistent-memory-production-agents): layered history/derived knowledge, selective retrieval, background consolidation, and using recalled knowledge in tasks.
- Installed 0.7.0 source: `databricks_agentkit/langgraph/memory.py`, `session_store.py`, `runtime/tool_manifest.py`, `_api_client.py`, `databricks_agentbricks/cli/pipeline.py`, and `services/dev_service.py`.

The installed CLI includes `memory pipeline runs get`; some documentation still describes REST-only run monitoring. The helper uses the verified CLI implementation. Research descriptions of an injected memory index and unified episodic search/fetch are not claims about this sample's four-tool adapter.
