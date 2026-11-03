# Validation record — November 2, 2026

The managed sample was checked against the installed
`databricks-agentbricks==0.8.0` CLI, its bundled OpenAI Agents template, and
`databricks/databricks-ai-bridge` source commit
`4a0225a6aa15024a9848468f3ab6882a8de49b58` (`main`, `0.9.0.dev0`).
The released CLI is the version used for the live checks below.

`agentbricks doctor .` passed all 8 managed-server onboarding checks. Ruff lint,
Ruff format, the three inventory tests, and the repository-wide
`bash scripts/validate.sh` passed.

The agent was deployed as `agent-bricks-lt-pro-1102` in the selected staging
workspace with one Medium App instance. Deployment reported `ready: true`,
provisioned a managed Runtime Store, and granted the App access to the existing
`system.ai.claude-haiku-4-5` model service. No Session Store, Memory Store, or
tracing experiment was bound.

A real nonstreamed `POST /api/invocations` completed with two model requests and
one `check_inventory` call. Its MX-100 answer correctly identified eight units
arriving in one business day and ten arriving in two. A later
`GET /api/invocations/{id}` returned the persisted result with the same answer,
tool audit, and usage.

The published CLI then ran a full 60-second dispatch window against
`/api/invocations` with SSE, concurrency 2, timeout 50, and no request cap:

| Completed | Failed | Peak in flight | Mean latency | p95 latency | Mean answer TTFT | Successful RPS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 34 | 0 | 2 | 3.63 s | 4.20 s | 1.80 s | 0.540 |

All 34 requests had measured TTFT and output-token usage; the total was 7,218
output tokens. The three workload cases ran 12/11/11 times. Elapsed time including
drain was 62.97 seconds. `scripts/check_results.py` passed on the CLI report and
private response capture. These results describe one staging deployment and local
load generator, not a sustained capacity limit.
