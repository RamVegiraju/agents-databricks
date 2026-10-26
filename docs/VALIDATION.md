# Validation record

Updated October 26, 2026. The current pro-code sequence is **01 CLI quickstart**, **02 Genie
supervisor**, **03 retail assistant**, and **04 horizontal scaling**. There is one current sample 01.

## Local checks

Run `bash scripts/validate.sh` from the repository root. It uses each sample's own environment and
checked-in lockfile, runs offline tests with live tests disabled, and runs `agentbricks doctor` for
each pro-code project.

| Current sample | Offline tests | Doctor | Live check |
| --- | ---: | ---: | --- |
| 01 CLI quickstart | 2 passed | 7/7 | Local and deployed clock-tool invocation completed |
| 02 Genie supervisor | 45 passed, 1 skipped | 7/7 | Sales and inventory specialists fetched Genie SQL and rows |
| 03 Retail assistant | 56 passed, 1 skipped | 7/7 | Genie query, policy search, and mixed request completed |
| 04 Horizontal scaling | 46 passed, 1 skipped | 7/7 | One- and three-instance Apps passed the Locust sweep |
| Lower-code Genie assets | 7 passed | n/a | Fixture tables and curated Genie Agents answered reviewed questions |
| Locust runner | 5 passed | n/a | Included in the two-App test above |

The local runner passed **161 tests** with **3 live tests skipped**. The live checks were run
separately using an explicitly selected workspace profile. Application readiness alone was not
treated as proof of agent behavior: the checks inspected tool calls, returned rows or citations,
and invocation results. The default Claude Sonnet 4.5 model hit a shared workspace quota during
the Genie and retail checks, so successful live requests used a Sonnet 5 request override.

The scaling run completed **623 requests** with no failures or incomplete requests. At 16 users,
throughput was **2.25 → 5.69 requests/s** and p95 latency was **9.3 → 4.4 s** for one versus
three fixed instances. MLflow recorded **625 `OK` traces** in the run window, including one
preflight invocation per App. See the [benchmark report](../pro-code/04-horizontal-scaling/BENCHMARK_RESULTS.md)
for the workload, aggregate files, and interpretation. This measured provisioned capacity, not
traffic-triggered autoscaling.

## Scope and reproducibility

- GitHub MCP in sample 03 has **not been validated** with a live credential.
- These checks do not establish worker crash recovery, production authorization boundaries, or
  general capacity limits. Each target workspace still needs its own permissions and live checks.
- The locks use public PyPI URLs. An environment-level `UV_INDEX_URL` pointing at another registry
  can make `uv lock --check` or `uv sync --locked` propose a registry-only rewrite. The sample
  commands use `--frozen` to install from the committed locks.
- The integration was checked against Agent Bricks CLI 0.6.0, Databricks SDK 0.154.0, installed
  AgentKit source, CLI help, and the linked official documentation in each sample README.

No workspace host, profile, resource ID, or credential is recorded in the tracked samples.
