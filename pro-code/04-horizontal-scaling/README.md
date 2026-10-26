# Horizontal scaling for an Agent Bricks App

Deploy this same LangGraph agent as two separate Databricks Apps: one with one fixed instance and
one with three. Locust tests each ready App at the same concurrency levels and prints live results.
Traffic does not automatically change either instance count. The default synthetic model workload
exercises the graph and durable stores without calling a model endpoint or tools.

## Run the demo

Choose an authorized Databricks profile. From the repository root:

```bash
cd pro-code/04-horizontal-scaling
uv sync --frozen --group dev
uv run --frozen agentbricks --profile <profile> deploy hs-one --source . --instances 1
uv run --frozen agentbricks --profile <profile> deploy hs-three --source . --instances 3
cd scripts/loadtest
uv sync --locked
uv run --locked python run_comparison.py \
  --profile <profile> \
  --one-app-name agent-bricks-hs-one \
  --three-app-name agent-bricks-hs-three \
  --users 1,4,8,16 --duration-seconds 30
```

Find both deployments under **Compute → Apps**. The comparison CLI waits for one and three active,
running instances, checks routing and completes a preflight invocation for each App, then shows live
Locust statistics in the terminal during each timed stage, then prints a final comparison with
throughput, latency, completed requests, and failures. It saves HTML/CSV and
`index.html` under `scripts/loadtest/results/comparison-<timestamp>/`. Both Apps remain deployed at
their fixed counts afterward. See the [walkthrough](HORIZONTAL_SCALING.md) for architecture and
benchmark details.

## Measured result

In a controlled run of this two-App workflow, throughput at 16 users was **2.23 req/s** with one
instance and **5.44 req/s** with three (**2.44×**); p95 latency was **8.8 → 4.3 s**. All 616 load
requests across the sweep completed without failure, and MLflow recorded 618 `OK` traces including
two preflight invocations. This is one short run, not a capacity estimate. See
[benchmark evidence](BENCHMARK_RESULTS.md).
