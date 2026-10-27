# Horizontal scaling benchmarks

## Agent Bricks 0.7.0 recheck, 2026-10-26

Both Medium Apps were redeployed from the same 0.7.0 source with fixed one- and three-instance
counts. The comparison CLI confirmed all instances were active and running, completed a preflight
agent invocation for each App, then ran 16 Locust users for 30 seconds per App with graceful drain.
The request exercised the synthetic graph workload and durable stores without an external model.

| Users | 1 instance req/s | 3 instances req/s | Gain | p95 latency, 1 → 3 | Completed, 1 / 3 | Failures |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 2.34 | 5.04 | **2.15×** | 9.4 → 6.0 s | 80 / 164 | 0 / 0 |

Rates use completed requests divided by elapsed time including drain. The anonymized aggregates
are [one instance](benchmark-results/2026-10-26-agentbricks-070/one-instance-controlled.json) and
[three instances](benchmark-results/2026-10-26-agentbricks-070/three-instances-controlled.json).
This is a short provisioned-capacity comparison, not a traffic-triggered autoscaling or general
capacity estimate. The Apps and managed services were not isolated from other workspace activity.

## Agent Bricks 0.6.0 historical runs

### Two-App live recheck, 2026-10-26

Both Medium Apps were redeployed from the same source with fixed one- and three-instance counts.
The CLI confirmed all configured instances were active and running, then ran Locust sequentially
for 30 seconds at each user level with graceful drain. Both used the same synthetic graph workload,
prompt, managed stores, and load runner.

| Concurrent users | 1 instance req/s | 3 instances req/s | Gain | p95 latency, 1 → 3 | Failures |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.66 | 0.65 | 0.99× | 2.6 → 3.7 s | 0 / 0 |
| 4 | 1.69 | 2.36 | 1.40× | 2.6 → 2.4 s | 0 / 0 |
| 8 | 2.44 | 3.66 | 1.50× | 5.3 → 2.6 s | 0 / 0 |
| 16 | 2.25 | 5.69 | **2.53×** | 9.3 → 4.4 s | 0 / 0 |

Locust recorded **230** completed requests on one instance and **393** on three, with no failures
or incomplete requests. MLflow had **625 `OK` traces** in the run window: those 623 load requests
plus one preflight invocation per App. Rates use completed requests divided by elapsed time,
including drain. This is one short synthetic run, not a capacity estimate. The anonymized
aggregates are [one instance](benchmark-results/2026-10-26-recheck/one-instance-controlled.json)
and [three instances](benchmark-results/2026-10-26-recheck/three-instances-controlled.json).

### Earlier two-App run, 2026-10-26

The standalone sample was deployed from the same checkout as two Medium Apps: one fixed at one
instance and one fixed at three. Both used the same synthetic model settings, prompt, managed
Session Store and Memory Store, and Locust runner. Each App had its own URL and Runtime Store.
Before load, Apps reported the matching configured, active, and running counts; 60 distinct routing
keys reached one and three server processes respectively. Locust then tested each ready App in
sequence for 30 seconds per user level, with graceful drain and fresh IDs per invocation.
The current demo CLI uses the Apps status checks and skips those historical routing probes.

| Concurrent users | 1 instance req/s | 3 instances req/s | Gain | p95 latency, 1 → 3 | Failures |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.78 | 0.72 | 0.92× | 2.2 → 2.2 s | 0 / 0 |
| 4 | 1.70 | 2.32 | 1.37× | 2.6 → 2.4 s | 0 / 0 |
| 8 | 2.33 | 3.72 | 1.60× | 4.5 → 2.6 s | 0 / 0 |
| 16 | 2.23 | 5.44 | **2.44×** | 8.8 → 4.3 s | 0 / 0 |

At 16 users, the final summaries recorded 72 and 176 completed requests. Across all eight
stages, all **616 started requests completed**, with no failures or incomplete requests. The
shared MLflow experiment had **618 `OK` traces**: those 616 requests plus one preflight
invocation per App. The final rates include the drain after each 30-second stage. This is one
short sweep in baseline-then-scaled order, so repeat it before treating the gain as a capacity
estimate. The anonymized aggregates are [one instance](benchmark-results/2026-10-26/one-instance-controlled.json)
and [three instances](benchmark-results/2026-10-26/three-instances-controlled.json).

## Prior same-App benchmark, 2026-10-23

The run used Medium App compute. The same deployed source, App URL, Runtime
Store, Session Store, prompt, and Locust runner were used within each one-versus-three pair.
Scaling was a manual Apps update with `compute_min_instances` and `compute_max_instances` both set
to 1 or both set to 3. App status reported the matching number of active and running instances;
60 distinct `X-Routing-Key` probes reached one process in the baseline and three in the scaled run.
This archived run preceded the extraction of this standalone sample. The agent and load-test code
used for the run are retained here; new deployments use separate store and experiment names.

## Controlled agent workload

The optional `SCALING_BENCHMARK_MOCK_MODEL=true` mode replaced the FMAPI call with a short synthetic
response and approximately 100 ms of CPU work per graph invocation. The request still traversed
`DurableAgentServer`, the LangGraph graph, the deployed Runtime Store, and the managed Session
Store. No tool calls or model tokens were measured. Each request used a fresh invocation and
session ID; Locust users sent another request immediately after each completion. Each stage ran
for 30 seconds, followed by a graceful drain of in-flight requests. The req/s figures below are
final completed requests divided by the elapsed time from Locust test start through shutdown;
p95 is over those completed requests. This full-run rate includes the drain time, rather than
representing a strict 30-second steady-state window.

| Concurrent users | 1 instance full-run req/s | 3 instances full-run req/s | Gain | 1 instance p95 | 3 instances p95 | Failures |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.58 | 0.71 | 1.22× | 2.4 s | 2.2 s | 0 / 0 |
| 4 | 1.70 | 2.34 | 1.37× | 2.8 s | 2.4 s | 0 / 0 |
| 8 | 2.28 | 3.75 | 1.65× | 4.9 s | 2.9 s | 0 / 0 |
| 16 | 2.39 | 5.33 | 2.23× | 8.8 s | 5.3 s | 0 / 0 |

Completed requests at 16 users were 85 over approximately 35.6 seconds and 172 over approximately
32.3 seconds respectively. Native Locust CSV snapshots were written before shutdown finished and
show 80 and 165 requests; the final summary records the additional completions. MLflow contains
exactly 85 and 172 `OK` traces in the corresponding 16-user windows, independently
confirming the final counts. The one-instance curve nearly
plateaued at 8–16 users while latency continued rising. This is one short run per configuration,
run in that order; it demonstrates a gain for this controlled workload, not a production capacity
estimate or a guarantee of linear scaling. Shared state services, client bandwidth, and workload
mix can change the result.

The aggregate summaries are saved in the repo with workspace and replica identifiers anonymized as
[one instance](benchmark-results/2026-10-23/one-instance-controlled.json) and
[three instances](benchmark-results/2026-10-23/three-instances-controlled.json). Native Locust
HTML/CSV reports are not committed. Reproduce the table from the checked-in aggregates with:

```bash
cd scripts/loadtest
uv run --frozen python compare.py \
  ../../benchmark-results/2026-10-23/one-instance-controlled.json \
  ../../benchmark-results/2026-10-23/three-instances-controlled.json
```

## Real model check

The unmodified agent used `system.ai.claude-sonnet-4-5`. One instance completed the 1- and
4-user stages without failures, but at 8 users 24 of 48 responses were HTTP 500. At three
instances, the 1-user stage succeeded, but 10 of 33 responses at 4 users were HTTP 500. App logs
showed the underlying `openai.RateLimitError` 429:
`REQUEST_LIMIT_EXCEEDED: Exceeded workspace input tokens per minute rate limit for
databricks-claude-sonnet-4-5`. MLflow independently shows 24 `OK` and 24 `ERROR` traces for the
one-instance 8-user stage, and 23 `OK` and 10 `ERROR` traces for the three-instance 4-user stage.
The real-model runs therefore do not establish an App throughput
gain; the workspace-wide FMAPI quota is a shared bottleneck, and the two runs were not isolated
from other workspace traffic. The saved aggregates are
[one instance](benchmark-results/2026-10-23/one-instance-real.json) and
[three instances](benchmark-results/2026-10-23/three-instances-real.json).

No change to `DurableAgentServer` was required. The current two-App sample uses the optional
benchmark model and checks instance counts through Apps status; it has no process diagnostic route.
