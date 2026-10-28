# Horizontal scaling for an Agent Bricks App

Deploy this same LangGraph agent as two separate Databricks Apps: one with one fixed instance and
one with three. Locust tests each ready App at the same concurrency levels and prints live results.
Traffic does not automatically change either instance count. The default synthetic model workload
exercises the graph and durable stores without calling a model endpoint or tools.

## Repository structure and adaptation

Focus on the controlled workload and the comparison runner: this demo compares fixed provisioned capacity, not autoscaling. For your own workload, first replace the synthetic model path and request mix, then compare identical code/configuration at different instance counts.

| File or directory | Role in this demo | Adapt for your own agent |
| --- | --- | --- |
| [agent/benchmark_model.py](agent/benchmark_model.py) | Synthetic CPU workload that avoids model-service quotas. | Keep for infrastructure comparisons; use a representative workload before drawing production-capacity conclusions. |
| [agent/agent.py](agent/agent.py) | Graph and synthetic-versus-real-model selection. | Review SCALING_BENCHMARK_MOCK_MODEL handling and your actual model/tool path. |
| [app.yaml](app.yaml) | Enables the mock model and sets SCALING_BENCHMARK_CPU_MS. | Set workload controls consistently across the compared deployments. |
| [agent.toml](agent.toml) | Store, tracing, framework, and deployment declarations. | Choose appropriate resources and names in your workspace; instance counts are passed to deploy. |
| [scripts/loadtest/run_comparison.py](scripts/loadtest/run_comparison.py) | Waits for ready Apps, runs staged comparisons, and builds the report. | Choose Apps, concurrency levels, duration, and readiness limits. |
| [scripts/loadtest/locustfile.py](scripts/loadtest/locustfile.py) | Request payloads, sessions, timing, and final request statistics. | Model realistic prompts, session reuse, request mix, and success criteria. |
| [scripts/loadtest/compare.py](scripts/loadtest/compare.py) | Compares exported benchmark measurements. | Adjust comparisons only when the measurement definition changes. |
| [scripts/loadtest/pyproject.toml](scripts/loadtest/pyproject.toml) | Separate uv environment for the load tester. | Install load-test dependencies here, independently of the agent environment. |
| [runtime/](runtime/) | Invocation, durable recovery, and browser/state integration. | Retain for comparable measurements; change only when the application contract changes. |
| [ui/](ui/) | Optional interactive chat and state inspection. | Use for inspection rather than generating benchmark traffic. |
| [tests/](tests/) | Offline agent/runtime/state checks. | Verify your workload changes before deploying. |
| [pyproject.toml](pyproject.toml) | Agent dependencies; uv.lock is its generated local lockfile. | Manage agent dependencies separately from scripts/loadtest. |
| [HORIZONTAL_SCALING.md](HORIZONTAL_SCALING.md) | Detailed architecture and benchmark procedure. | Use as the experiment design reference. |
| [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) | Checked-in evidence from earlier runs. | Record new measurements separately; generated reports appear under scripts/loadtest/results/ after execution. |

## Run the demo

Use a Databricks CLI profile for a workspace where you can create Apps, managed stores, and an
MLflow experiment, with capacity for four App instances. These commands use `rsync` to make two
temporary deployment source copies.
If needed, create the profile with `databricks auth login --host <workspace-url> --profile <profile>`.
From the repository root:

```bash
cd pro-code/03-horizontal-scaling
databricks auth profiles
uv sync --frozen --group dev
demo_sources="$(mktemp -d)"
rsync -a --exclude '.venv' --exclude '.env' --exclude 'results' ./ "$demo_sources/one/"
rsync -a --exclude '.venv' --exclude '.env' --exclude 'results' ./ "$demo_sources/three/"
uv run --frozen agentbricks --profile <profile> deploy hs-one --source "$demo_sources/one" --instances 1
uv run --frozen agentbricks --profile <profile> deploy hs-three --source "$demo_sources/three" --instances 3
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

The two source copies start from the same code and keep the CLI's App-specific `agent.toml` and
`app.yaml` edits separate. The App and load tester have separate uv projects; run the load test commands from
`scripts/loadtest`. `--profile` selects the workspace; deploy creates the stores and experiment
declared in `agent.toml` there. Use unused deployment names if `hs-one` or `hs-three` already exist,
and pass the corresponding `agent-bricks-<name>` values to the comparison command. Review the
Memory Store, Session Store, and tracing names in `agent.toml` before using another workspace;
choose unused names if existing resources there have different access settings.

## Measured result

In the Agent Bricks CLI 0.7.0 recheck at 16 users, throughput was **2.34 req/s** with one instance
and **5.04 req/s** with three (**2.15×**); p95 latency was **9.4 → 6.0 s**. All 244 load requests
completed without failure. This is one short provisioned-capacity run, not a capacity estimate. See
[benchmark evidence](BENCHMARK_RESULTS.md).
