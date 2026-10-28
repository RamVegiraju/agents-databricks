# 03 · App scaling

Compare the same agent on **one versus three fixed App instances**. Locust reports throughput,
latency, and failures. This demonstrates provisioned capacity, not automatic scaling. The default synthetic CPU workload
exercises the graph and durable stores without calling a model endpoint or tools.

## Before you start

Complete the [shared setup](../../docs/GETTING_STARTED.md). You need permission to create Apps,
managed stores, and tracing, with capacity for four instances. These commands also use `rsync`.

```bash
cd pro-code/03-horizontal-scaling
export PROFILE="my-workspace"
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen pytest -q
```

## Run

Create two deployment copies so each App keeps its own generated configuration:

```bash
SOURCES="$(mktemp -d)"
rsync -a --exclude .venv --exclude .env --exclude results ./ "$SOURCES/one/"
rsync -a --exclude .venv --exclude .env --exclude results ./ "$SOURCES/three/"
uv run --frozen agentbricks --profile "$PROFILE" deploy hs-one --source "$SOURCES/one" --instances 1
uv run --frozen agentbricks --profile "$PROFILE" deploy hs-three --source "$SOURCES/three" --instances 3
cd scripts/loadtest
uv sync --frozen
uv run --frozen python run_comparison.py \
  --profile "$PROFILE" \
  --one-app-name agent-bricks-hs-one --three-app-name agent-bricks-hs-three \
  --users 1,4,8,16 --duration-seconds 30
```

Choose unused deployment names if these already exist, and update the comparison arguments.
Review store and tracing names in `agent.toml` for your workspace before deploying.

## Inspect the result

The runner checks instance readiness, invokes each App, then tests them sequentially. Compare
requests/second, p95 latency, and completed/failed requests at the same user count. Open the generated
`index.html` under `scripts/loadtest/results/comparison-<timestamp>/` for the report.

Both Apps remain at their fixed instance counts. Return to the agent environment before stopping them:

```bash
cd ../..  # From scripts/loadtest back to this sample.
uv run --frozen agentbricks --profile "$PROFILE" deployments stop agent-bricks-hs-one --yes
uv run --frozen agentbricks --profile "$PROFILE" deployments stop agent-bricks-hs-three --yes
```

## Customize

| File | Purpose / what to change |
| --- | --- |
| [agent/benchmark_model.py](agent/benchmark_model.py) | Workload operations and cost of each request. |
| [agent/agent.py](agent/agent.py) | Agent model and tool loop. |
| [scripts/loadtest/locustfile.py](scripts/loadtest/locustfile.py) | Request mix and pacing. |
| [scripts/loadtest/run_comparison.py](scripts/loadtest/run_comparison.py) | Deployment selection and load stages. |
| [scripts/loadtest/pyproject.toml](scripts/loadtest/pyproject.toml) | Separate load-tester dependencies. |
| [agent.toml](agent.toml), [app.yaml](app.yaml) | Bindings and App startup. |
| [runtime/](runtime/), [ui/](ui/), [tests/](tests/) | Server, optional inspection UI, and offline checks. |
| [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Agent dependencies and generated lockfile. |

See [HORIZONTAL_SCALING.md](HORIZONTAL_SCALING.md) for experiment details and
[BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) for measured results. Short runs are not capacity guarantees.
