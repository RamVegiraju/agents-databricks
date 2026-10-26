# Horizontal scaling walkthrough

See [the 2026-10-23 live benchmark](BENCHMARK_RESULTS.md) for measured results and the model
quota limitation observed in the real-agent run.

This standalone sample uses the same LangGraph agent as Hello World to show an App serving requests
from more than one replica and to measure end-to-end agent throughput. It changes the **fixed**
instance count from 1 to 3. Databricks Apps documentation does not describe a request-rate or CPU
trigger that automatically changes this count. The scaling event in this demo is the operator's
instance-count update.

## What the platform and AgentKit do

- Databricks puts 1–5 instances behind one App URL. Each instance runs this project's single
  `uvicorn` server process. Compute cost grows with instance count. A workspace can have up to 20
  horizontally scaled Apps by default. Databricks recommends at least 2 instances for availability.
  Newly created scaled Apps have no pre-installed Python libraries; this project's `pyproject.toml`
  declares its runtime dependencies and `app.yaml` starts them through `uv run`.
- The router gives browsers a sticky cookie. API callers can send `X-Routing-Key`; this benchmark
  uses a fresh UUID for each new session and keeps that value as its routing key. Affinity is
  best effort, so a session can move during failures, deployments, or rebalancing.
- `DurableAgentServer` already uses a deployed, shared Runtime Store for invocation status,
  results, events, and recovery. Its `recover` hook is registered in `runtime/main.py`. No
  replica-aware server change is needed.
- The LangGraph checkpointer needs the **bound managed Session Store** in `agent.toml` for
  conversation state to survive a move. An in-process checkpointer in `agentbricks dev` cannot
  demonstrate cross-replica continuity. The existing Memory Store is separate from both stores.
- `/api/replica` returns a random ID generated once per server process. It is diagnostic only and
  holds no user or conversation state. Probe it with many distinct routing keys to see distribution.

## Deploy and measure

Choose a named workspace profile yourself. This project never selects one implicitly. The profile
must have permissions to deploy Apps, provision the stores in `agent.toml`, call the selected model,
and invoke the deployed App. The example is a single-user sandbox, so run the load test only with
your own authorized identity. `APP_BEARER_TOKEN` is optional for an M2M caller with App access;
otherwise the benchmark gets a U2M token from `databricks auth token --profile`.

```bash
cd pro-code/04-horizontal-scaling
databricks auth profiles
uv sync --frozen --group dev
uv run --frozen agentbricks doctor .
uv run --frozen agentbricks --profile <profile> deploy horizontal-scaling-demo --source . --instances 1
databricks apps get agent-bricks-horizontal-scaling-demo --profile <profile> -o json
```

The last output should show a running App, a URL, and `compute_min_instances` and
`compute_max_instances` of 1. Use that URL below. Run the same prompt, duration, and Locust user
levels at each instance count. Each request gets a fresh invocation ID and session ID, so the
server's per-session serialization does not turn the benchmark into a single queue. The load
generator lives in a separate environment and uses Locust for scheduling, latency histograms, CSV,
and HTML reports. Its foreground POST measures the complete agent invocation.

```bash
cd scripts/loadtest
uv sync --locked
uv run --locked python run.py \
  --profile <profile> \
  --app-url https://<app-url> \
  --label one-instance \
  --users 1,4,8,16 --duration-seconds 30 \
  --output-dir results/one-instance
```

**Trigger the scale change** on the same App with the Databricks Apps CLI:

```bash
databricks apps create-update agent-bricks-horizontal-scaling-demo \
  --json '{"update_mask":"compute_min_instances,compute_max_instances","app":{"compute_min_instances":3,"compute_max_instances":3}}' \
  --profile <profile>
databricks apps get agent-bricks-horizontal-scaling-demo --profile <profile> -o json
```

Wait for the update to finish, then confirm `compute_min_instances` and
`compute_max_instances` are 3. The docs say the App keeps serving traffic during a count change.
The Agent Bricks CLI can also change the count with `uv run --frozen agentbricks --profile
<profile> deploy horizontal-scaling-demo --source . --instances 3`; that path includes a new source
deployment, so the Apps update isolates the compute change more clearly. Run the benchmark again:

```bash
uv run --locked python run.py \
  --profile <profile> \
  --app-url https://<app-url> \
  --label three-instances \
  --users 1,4,8,16 --duration-seconds 30 \
  --output-dir results/three-instances
uv run --locked python compare.py \
  results/one-instance/summary.json results/three-instances/summary.json
```

Each `users-*` directory holds native Locust HTML and CSV reports. The comparison table shows
full-run throughput gain, p95 latency, and failures at each concurrency level. The full-run rate
divides the final completed count by elapsed time through graceful shutdown, including the drain
of in-flight requests; native CSV/HTML snapshots can be written before the final count settles.
Show the App's configured count and the benchmark's `replica_count_observed` alongside it. An
observed count of 3 proves the routing probe reached three server processes; it does not prove
every invocation was evenly distributed. The gain at each level is the three-instance full-run
rate divided by the one-instance full-run rate. Run more than once and compare at the same load. If the model
endpoint, store, quota, or load generator saturates first, throughput may show little gain. Check
the run's MLflow traces and App telemetry before attributing a plateau to Apps compute.

For a controlled App-capacity run when FMAPI quotas dominate, add these entries to the existing
`env` list in `app.yaml` and redeploy once before measuring either instance count:

```yaml
- name: SCALING_BENCHMARK_MOCK_MODEL
  value: "true"
- name: SCALING_BENCHMARK_CPU_MS
  value: "100"
```

The mock returns a short synthetic message after bounded CPU work. It still runs the real graph
and durable stores, but does not call the model service or exercise tools. Use the same values
for both measured configurations. Remove the entries and redeploy to return to the real model.
After the demo, set both instance values back to 1 if the extra capacity is no longer needed.

## Agent Bricks CLI detail

`databricks-agentbricks==0.6.0`, pinned in this example, accepts `agentbricks deploy
--instances 1..5`. In the 0.6.0 source, it creates a new App with both compute minimum and maximum
set to that count. For an existing App, it sends a masked `databricks apps create-update` request.
Omitting `--instances` preserves an existing App's scale. The JSON update command above was
validated against the selected workspace during the live benchmark.
No change to `DurableAgentServer` or this project's invocation adapter is needed for scaling.

## References

- [Horizontal scaling for Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/horizontal-scaling)
- [Agent Server and shared run state](https://docs.databricks.com/aws/en/agents/deploy/agent-server)
- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [Agent Bricks 0.6.0 deploy option](https://github.com/databricks/databricks-ai-bridge/blob/databricks-agentbricks-v0.6.0/integrations/agentbricks/src/databricks_agentbricks/cli/deploy.py)
- [Agent Bricks 0.6.0 Apps client](https://github.com/databricks/databricks-ai-bridge/blob/databricks-agentbricks-v0.6.0/integrations/agentbricks/src/databricks_agentbricks/clients/apps_client.py)
- [AgentKit runtime architecture](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentkit/runtime/ARCHITECTURE.md)
- [Agent Bricks Locust load-test PR](https://github.com/databricks/databricks-ai-bridge/pull/785) — useful design reference; not part of the pinned 0.6.0 release
