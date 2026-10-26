# Manual horizontal scaling for an Agent Bricks App

This standalone LangGraph agent uses the same durable server, Session Store, and Memory Store at
one and three fixed Databricks App instances. A diagnostic route confirms that requests reach
distinct server processes; Locust measures completed invocations at each concurrency level.
The CLI changes the count explicitly; traffic does not trigger autoscaling.
The agent has one local UTC clock tool and managed memory tools; no Genie or MCP service is bound.
The controlled benchmark calls neither the clock nor the memory tools.

## Measured result

In a controlled run with a short synthetic model response and about 100 ms of CPU work per
invocation, three instances handled more concurrent requests:

| Concurrent users | 1 instance | 3 instances | Gain | p95 latency, 1 → 3 |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 1.70 req/s | 2.34 req/s | 1.37× | 2.8 → 2.4 s |
| 8 | 2.28 req/s | 3.75 req/s | 1.65× | 4.9 → 2.9 s |
| 16 | 2.39 req/s | 5.33 req/s | **2.23×** | 8.8 → 5.3 s |

These full-run rates include the drain after each 30-second load period. All controlled requests
completed without failure; MLflow trace counts matched the Locust totals. A real-model run hit a
shared model quota, so it could not establish an App throughput gain. This is one short run per
configuration, not a capacity estimate. See [benchmark evidence](BENCHMARK_RESULTS.md).

## Run the live comparison

Requires Python 3.11+, `uv`, Databricks CLI, an explicitly chosen profile, and access to deploy an
App and its stores. From the repository root:

```bash
cd pro-code/04-horizontal-scaling
uv sync --frozen --group dev
uv run --frozen pytest -q
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> deploy horizontal-scaling-demo --source . --instances 1
cd scripts/loadtest
uv sync --locked
uv run --locked python run_comparison.py \
  --profile <profile> --app-name agent-bricks-horizontal-scaling-demo \
  --users 1,4,8,16 --duration-seconds 30
```

Locust prints live CLI statistics. The command saves native HTML/CSV for every user level plus a
comparison page under `scripts/loadtest/results/comparison-<timestamp>/`, then restores the App's
original instance count. The sample's `app.yaml` enables the controlled benchmark model by
default. Remove those two environment entries and redeploy to try the real model; shared model
quotas can then limit throughput. See the [walkthrough](HORIZONTAL_SCALING.md) for the manual
commands and design details. `DurableAgentServer` needs no scaling change.
