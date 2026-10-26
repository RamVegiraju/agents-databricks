# Horizontal scaling benchmark, 2026-10-23

Workspace: `e2-dogfood-staging` (`6051921418418893`). App:
`agent-bricks-hello-memory-demo`, Medium compute. The same deployed source, App URL, Runtime
Store, Session Store, prompt, and Locust runner were used within each one-versus-three pair.
Scaling was a manual Apps update with `compute_min_instances` and `compute_max_instances` both set
to 1 or both set to 3. App status reported the matching number of active and running instances;
60 distinct `X-Routing-Key` probes reached one process in the baseline and three in the scaled run.

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
show 80 and 165 requests; the final summary records the additional completions. The
[MLflow experiment](https://e2-dogfood.staging.cloud.databricks.com/ml/experiments/1127448673891747?compareRunsMode=TRACES)
contains exactly 85 and 172 `OK` traces in the corresponding 16-user windows, independently
confirming the final counts. The one-instance curve nearly
plateaued at 8–16 users while latency continued rising. This is one short run per configuration,
run in that order; it demonstrates a gain for this controlled workload, not a production capacity
estimate or a guarantee of linear scaling. Shared state services, client bandwidth, and workload
mix can change the result.

The raw aggregate summaries are saved in the repo as
[one instance](benchmark-results/2026-10-23/one-instance-controlled.json) and
[three instances](benchmark-results/2026-10-23/three-instances-controlled.json). Local Locust
HTML/CSV reports from the original run are under `scripts/loadtest/results/one-instance-mock` and
`scripts/loadtest/results/three-instances-mock` locally (ignored by Git). Reproduce the table from
the checked-in aggregates with:

```bash
cd scripts/loadtest
uv run --locked python compare.py \
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
from other workspace traffic. These raw runs are under `results/one-instance` and
`results/three-instances` locally. The saved aggregates are
[one instance](benchmark-results/2026-10-23/one-instance-real.json) and
[three instances](benchmark-results/2026-10-23/three-instances-real.json).

No change to `DurableAgentServer` was required. The sample adds only a process diagnostic route
and the optional benchmark model. After testing, the benchmark environment variables are removed
from the deployed App and its instance count is returned to one.
