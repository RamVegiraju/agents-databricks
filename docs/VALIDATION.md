# Validation record

Verified locally on October 20, 2026. This is a source/docs and offline behavior record, not a
workspace acceptance report. No Databricks resource creation, deployment, remote model call,
Genie query, pipeline run or external MCP call was performed for this build.

## Versions and reproducibility

| Component | Inspected/tested version |
| --- | --- |
| Agent Bricks / AgentKit | databricks-agentbricks 0.6.0, installed PyPI release |
| Databricks workspace SDK | 0.154.0 |
| Databricks CLI | 1.17.0 (local help only during this build) |
| LangGraph | 1.2.16 |
| LangChain | 1.4.6 |
| Databricks LangChain integration | 0.21.0 |
| Python | 3.12.14 |

All four projects have uv.lock and were synced into separate .venv environments. Validation used
`uv run --offline --locked pytest -q` in each project; no transitive resolution occurred during tests.
The packages' broader Python/platform compatibility has not been tested. The local tooling
`.agentbricks-current` environment is ignored and is not required by the examples.

## Results

| Project | Offline tests | Explicit live tests skipped | Agent Bricks doctor |
| --- | ---: | ---: | --- |
| 01 Hello World + memory | 46 passed | 1 | 7/7 passed |
| 02 Genie supervisor | 43 passed | 1 | 7/7 passed |
| 03 Retail assistant | 50 passed | 1 | 7/7 passed |
| Lower-code Genie assets | 6 passed | 0 | Not applicable: assets, not an AgentKit app |

145 tests passed, 3 live tests skipped. Ruff checks passed for all authored Python and generated
runtime/tests after formatting/import cleanup. The introductory app preserves generated ValueError
HTTP payload semantics through its explicit TRY004 lint exception. Each pro-code suite reports an
upstream Unity Catalog toolkit Pydantic deprecation warning; it does not fail the tests.

The scripts/validate.sh runner forces live tests off and performs the same locked offline checks.
It requires uv plus each project's previously installed environment/cache.

## Evidence and boundaries

| Integration | Source checked | Behavior tested offline | Not proven |
| --- | --- | --- | --- |
| LangGraph runtime | Released template, AgentKit runtime/app.py, execution.py, durability/execution.py, langgraph/session_store.py and responses.py | Invocation routes, event serialization, checkpoint/recovery input mapping, actual graph execution | Worker crash/restart behavior on Databricks Apps |
| Memory | AgentKit langgraph/memory.py, memory_store.py, session_store.py and runtime/tool_manifest.py | Actual released remember/recall/list/forget tools against injected storage; cross-chat recall, different actor filtering, pipeline-only tools, no system-memory checkpoint persistence | Memory service access, BM25 ranking behavior, extraction quality |
| Transcript bridge | Documented plain message shape; authored agent/transcript.py | Text-only filtering, stable actor/invocation identity, normal replay deduplication, ownership/mismatch rejection | Cross-service atomicity or exactly-once recording after worker loss |
| Genie supervisor | AgentKit langgraph/genie.py and runtime/genie.py; SDK0.154.0 signatures | Both-domain delegation, specialist tool isolation, real adapter parsing of injected Genie responses/query rows | Actual Genie/SQL authorization or model routing accuracy |
| AI Search | SDK service/vectorsearch.py typed request/response classes | Returned-column manifest parsing, citation propagation, graph-to-search call, index spec shape | Endpoint/index availability, embedding generation, live retrieval quality |
| Unstructured ingestion | SDK SQL statement parameter types and cancel-on-timeout behavior | Deterministic chunks, identifier validation, parameterized MERGE/CDF requests | Executed Delta SQL, source/table/index consistency after live sync |
| External MCP | SDK ConnectionType.HTTP, McpServiceConfig classes and AgentKit MCP binding source | Typed schema-level connection/MCP Service request shapes, preview does not resolve auth or print tokens | Provider credential acceptance, tool discovery/execution, outbound networking |
| Genie definition assets | Current version2 serialized_space docs, SDK passes serialized JSON, CLI create/start/get help | Required/sorted fields, fixture metrics and nine example SELECTs against VALUES in SQLite including snapshot/fanout checks | Genie server schema acceptance, Databricks SQL execution, generated query quality |

Setup scripts in sample03 default to offline preview. They require --apply and an explicit profile
for workspace mutations; token/warehouse requirements are enforced before applying. Startup does not
create external resources. Bound stores are handled by a later authorized Agent Bricks deployment.

## Corrections based on implementation evidence

- CLI0.6.0 `tools add genie-agent` is the actual command; `tools add genie` is not used.
- CLI0.6.0 `dev --help` states memory is disabled, sessions are in-process and MLflow is local.
  Some generated contract prose said dev might provision stores; the examples correct that prose.
- Runtime store resolvers in runtime/tool_manifest.py read explicit arguments/environment. Their
  older adapter docstrings mention direct manifest fallback; do not depend on that. Deployment
  resolves agent.toml into runtime environment; direct local managed-state startup sets it explicitly.
- LangGraph checkpoint blobs are unreadable by memory pipelines. Sample01 additionally writes
  user/assistant text transcripts; samples02/03 do not claim pipeline extraction from checkpoints.
- Actor IDs are grouping, not authorization. SDK saver lookup is keyed by thread ID. These are
  single-user/team demos using server-selected DEMO_ACTOR_ID; production identity and ownership
  enforcement requires additional application integration. Store boundaries enforce service access.
- Detailed memory retrieval docs specify BM25 full-text retrieval without vector similarity search,
  while overview prose says semantic search. No unsupported vector-search guarantee is made here.
- Modern external MCP registration uses a schema-level HTTP connection plus an MCP Service; the
  agent connects through /ai-gateway/mcp-services/<full-name>, not the legacy external proxy pattern.
- Genie documentation contains older version1 examples but explicitly requires version2 for new
  serialized agent definitions. Assets use version2; service-side acceptance remains untested.

## Primary references

- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [Agent Server](https://docs.databricks.com/aws/en/agents/deploy/agent-server)
- [Agent Runtime](https://docs.databricks.com/aws/en/agents/deploy/agent-runtime)
- [AgentKit release/source repository](https://github.com/databricks/databricks-ai-bridge/tree/main/integrations/agentbricks)
- [Session and memory integration tutorial](https://docs.databricks.com/aws/en/agents/agent-memory/existing-agent-tutorial)
- [Session stores](https://docs.databricks.com/aws/en/agents/agent-memory/managed-sessions)
- [Memory stores](https://docs.databricks.com/aws/en/agents/agent-memory/managed-memory)
- [Memory pipelines](https://docs.databricks.com/aws/en/agents/agent-memory/memory-pipelines)
- [LangGraph model/tool loop](https://docs.langchain.com/oss/python/langgraph/quickstart)
- [Genie serialized_space validation](https://docs.databricks.com/aws/en/genie-agents/conversation-api#validation-rules-for-serialized_space)
- [AI Search index creation](https://docs.databricks.com/aws/en/ai-search/create-ai-search)
- [MCP API/SDK registration](https://docs.databricks.com/aws/en/ai-gateway/mcp-service-reference)
- [HTTP connection settings](https://docs.databricks.com/aws/en/query-federation/http)
- [GitHub hosted MCP and readonly endpoint](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md)

The cited live source main branches can advance independently of released wheels. Where relevant,
we inspected the installed 0.6.0/0.154.0 implementation rather than assuming main matched the release.
