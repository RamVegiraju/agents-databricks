# Validation record

Updated November 2, 2026. The sequence is **01 CLI**, **02 memory**, **03 agent load test**,
**04 horizontal scaling**, **05 Genie supervisor**, and **06 MCP**. Sample **07 retail
assistant** combines the integrations as an advanced example.

## Local checks

Run `bash scripts/validate.sh` from the repository root. It uses each sample's own environment and
lockfile, runs offline tests with live tests disabled, and runs `agentbricks doctor` for
managed-server pro-code projects. Sample 03 generates its local lock from public PyPI and uses
a custom server, so the managed onboarding check does not apply.

| Current sample | Offline tests | Doctor | Live check |
| --- | ---: | ---: | --- |
| 01 CLI quickstart | 2 passed | 8/8 | Deployed clock-tool invocation completed |
| 02 Agent memory | 61 passed, 1 skipped | 8/8 | Fresh-resource pipeline rehearsal, four natural-language retrieval spot checks, and user-reported browser acceptance; [evidence](../pro-code/02-agent-memory/VALIDATION.md) |
| 03 Agent load test | 3 passed | Custom server | Real inventory agent completed 10/10 hosted requests with native loadtest CLI 0.8.0; [evidence](../pro-code/03-agent-load-test/VALIDATION.md) |
| 04 Horizontal scaling | 46 passed, 1 skipped | 8/8 | One- and three-instance Apps passed the 0.7.0 Locust recheck |
| 05 Genie supervisor | 45 passed, 1 skipped | 8/8 | Sales specialist returned Genie SQL and fetched rows |
| 06 MCP server | 1 passed | 8/8 | Managed `web_search` MCP returned a tool result and cited answer |
| 07 Retail assistant | 56 passed, 1 skipped | 8/8 | Policy search returned a cited source passage |
| Lower-code Genie assets | 7 passed | n/a | Fixture tables and curated Genie Agents answered reviewed questions |
| Locust runner | 5 passed | n/a | Included in the two-App test above |

The earlier local runner passed **223 tests** with **4 live tests skipped** on Agent Bricks CLI 0.7.0.
Sample 03 adds three separate offline tests on the 0.8.0 CLI.
The October 28 push checks reran all offline suites and all six onboarding checks; they did not
rerun every historical live integration or the load benchmark. Live results below were inspected
through tool calls/results, not only App readiness. Earlier Genie, retail, and direct-memory
checks used a Sonnet 5 override. The October 27 memory pipeline and natural-language tests used
`system.ai.claude-sonnet-4-5`; the MCP check used its default model.

The 0.7.0 scaling recheck completed **244 requests** at 16 users with no failures or incomplete
requests. Throughput was **2.34 → 5.04 requests/s** and p95 latency **9.4 → 6.0 s** for one versus
three fixed instances. The [benchmark report](../pro-code/04-horizontal-scaling/BENCHMARK_RESULTS.md)
contains anonymized aggregates and earlier 0.6.0 measurements. This measures provisioned capacity,
not traffic-triggered autoscaling.

## Scope and reproducibility

- The managed web-search MCP in sample 06 was validated live. The optional GitHub MCP in sample 07
  has **not been validated** with a live credential.
- These checks do not establish worker crash recovery, production authorization boundaries, or
  general capacity limits. Each target workspace still needs its own permissions and live checks.
- The committed locks use public PyPI URLs. Sample 03 generates its own local locks. An environment-level `UV_INDEX_URL` pointing at another registry
  can make `uv lock --check` or `uv sync --locked` propose a registry-only rewrite. The sample
  commands use `--frozen` to install from the committed locks.
- The current packages and CLI commands were checked against Agent Bricks CLI 0.7.0,
  Databricks SDK 0.157.0, installed AgentKit source, CLI help, and the linked official
  documentation in each sample README.

Reusable startup configuration excludes deployment-generated connection settings. The memory
sample's explicitly labeled validation evidence records its demo profile/resource identifiers
for reproducibility; those identifiers are not credentials. Tokens and local credential files
are excluded from version control.
