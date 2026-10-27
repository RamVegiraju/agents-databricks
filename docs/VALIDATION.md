# Validation record

Updated October 26, 2026. The video sequence is **01 CLI**, **02 memory**, **03 horizontal
scaling**, **04 Genie supervisor**, and **05 MCP**. Sample **06 retail assistant** combines the
integrations as an advanced example.

## Local checks

Run `bash scripts/validate.sh` from the repository root. It uses each sample's own environment and
checked-in lockfile, runs offline tests with live tests disabled, and runs `agentbricks doctor` for
each pro-code project.

| Current sample | Offline tests | Doctor | Live check |
| --- | ---: | ---: | --- |
| 01 CLI quickstart | 2 passed | 8/8 | Deployed clock-tool invocation completed |
| 02 Agent memory | 46 passed, 1 skipped | 8/8 | Remembered in one session, recalled in another, then forgot the fact |
| 03 Horizontal scaling | 46 passed, 1 skipped | 8/8 | One- and three-instance Apps passed the 0.7.0 Locust recheck |
| 04 Genie supervisor | 45 passed, 1 skipped | 8/8 | Sales specialist returned Genie SQL and fetched rows |
| 05 MCP server | 1 passed | 8/8 | Managed `web_search` MCP returned a tool result and cited answer |
| 06 Retail assistant | 56 passed, 1 skipped | 8/8 | Policy search returned a cited source passage |
| Lower-code Genie assets | 7 passed | n/a | Fixture tables and curated Genie Agents answered reviewed questions |
| Locust runner | 5 passed | n/a | Included in the two-App test above |

The local runner passed **208 tests** with **4 live tests skipped** on Agent Bricks CLI 0.7.0.
The live checks used an explicitly selected workspace profile and inspected tool calls and results,
not only App readiness. The Genie, retail, and memory checks used a Sonnet 5 request override to
avoid the shared Sonnet 4.5 quota encountered in earlier tests. The MCP check used its default model.

The 0.7.0 scaling recheck completed **244 requests** at 16 users with no failures or incomplete
requests. Throughput was **2.34 → 5.04 requests/s** and p95 latency **9.4 → 6.0 s** for one versus
three fixed instances. The [benchmark report](../pro-code/03-horizontal-scaling/BENCHMARK_RESULTS.md)
contains anonymized aggregates and earlier 0.6.0 measurements. This measures provisioned capacity,
not traffic-triggered autoscaling.

## Scope and reproducibility

- The managed web-search MCP in sample 05 was validated live. The optional GitHub MCP in sample 06
  has **not been validated** with a live credential.
- These checks do not establish worker crash recovery, production authorization boundaries, or
  general capacity limits. Each target workspace still needs its own permissions and live checks.
- The locks use public PyPI URLs. An environment-level `UV_INDEX_URL` pointing at another registry
  can make `uv lock --check` or `uv sync --locked` propose a registry-only rewrite. The sample
  commands use `--frozen` to install from the committed locks.
- The current packages and CLI commands were checked against Agent Bricks CLI 0.7.0,
  Databricks SDK 0.157.0, installed AgentKit source, CLI help, and the linked official
  documentation in each sample README.

No workspace host, profile, resource ID, or credential is recorded in the tracked samples.
