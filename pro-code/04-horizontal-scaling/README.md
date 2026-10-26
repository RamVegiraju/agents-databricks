# Horizontal scaling for an Agent Bricks App

Deploy this same LangGraph agent as two separate Databricks Apps: one with one fixed instance and
one with three. Locust tests each ready App at the same concurrency levels and prints live results.
Traffic does not automatically change either instance count. The default synthetic model workload
exercises the graph and durable stores without calling a model endpoint or tools.

## Run the demo

Use a Databricks CLI profile for a workspace where you can create Apps, managed stores, and an
MLflow experiment, with capacity for four App instances. From the repository root:

```bash
cd pro-code/04-horizontal-scaling
uv sync --frozen --group dev
uv run --frozen agentbricks --profile <profile> deploy hs-one --source . --instances 1
uv run --frozen agentbricks --profile <profile> deploy hs-three --source . --instances 3
cd scripts/loadtest
uv sync --frozen
uv run --frozen python run_comparison.py \
  --profile <profile> \
  --one-app-name agent-bricks-hs-one \
  --three-app-name agent-bricks-hs-three \
  --users 1,4,8,16 --duration-seconds 30
```

Find both deployments under **Compute → Apps**. The comparison CLI waits for one and three active,
running instances and completes a preflight invocation for each App. It shows live
Locust statistics in the terminal during each timed stage, then prints a final comparison with
throughput, latency, completed requests, and failures. It saves HTML/CSV and
`index.html` under `scripts/loadtest/results/comparison-<timestamp>/`. Both Apps remain deployed at
their fixed counts afterward. See the [walkthrough](HORIZONTAL_SCALING.md) for architecture and
benchmark details.

The App and load tester have separate uv projects; run the load test commands from
`scripts/loadtest`. `--profile` selects the workspace; deploy creates the stores and experiment
declared in `agent.toml` there. Use unused deployment names if `hs-one` or `hs-three` already exist,
and pass the corresponding `agent-bricks-<name>` values to the comparison command.

## Measured result

In the latest controlled run, throughput at 16 users was **2.25 req/s** with one instance and
**5.69 req/s** with three (**2.53×**); p95 latency was **9.3 → 4.4 s**. All 623 load requests
across the sweep completed without failure, and MLflow recorded 625 `OK` traces including two
preflight invocations. This is one short run, not a capacity estimate. See
[benchmark evidence](BENCHMARK_RESULTS.md).
