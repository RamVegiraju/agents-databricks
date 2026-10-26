# Two-App horizontal scaling walkthrough

The [README](README.md) has the complete deploy and Locust commands. This demo deploys identical
source to two separate Databricks Apps, fixed at one and three instances. The comparison CLI reads
their URLs, waits for both Apps to report the expected configured, active, and running counts, then
tests them sequentially. It never changes App capacity. Each App keeps its own URL and Runtime
Store; the declared Session Store and Memory Store bindings are shared. Both Apps should use the
same compute size and synthetic workload settings.

## Request path

```text
Locust → App URL → Apps router → instance → Uvicorn → DurableAgentServer → LangGraph
                                                   ↘ Runtime Store / Session Store
```

Each instance runs one Uvicorn worker by default. Before testing, the CLI checks that Apps reports
one and three configured, active, and running instances.
For every invocation, Locust sends a fresh invocation ID and session ID. The session ID also serves
as that request's routing key, so independent requests can reach different processes. Sticky
routing is best effort. The managed Session Store preserves graph checkpoints across replicas;
`DurableAgentServer` uses the shared Runtime Store for invocation status and recovery. The Memory
Store holds long-term facts and is separate from both.

The sample's `app.yaml` enables `SCALING_BENCHMARK_MOCK_MODEL=true` and
`SCALING_BENCHMARK_CPU_MS=100`. The synthetic response still runs through the graph and stores,
but does not call the model service, clock, or memory tools. To test the real model, remove those
settings and redeploy both Apps from the same source. Model quotas can then cap throughput.

## Reading the results

The CLI runs each requested user level for 30 seconds by default, drains in-flight requests, and
uses final completed requests divided by elapsed time for its full-run rate. It reports p95 latency
and failures, and links to native Locust HTML/CSV for each level. CSV/HTML may snapshot before the
last drained requests; `final-summary.json` and `summary.json` include them. Compare runs with the
same prompt, user levels, compute size, source, and store bindings. The CLI checks the measurable
parts of that setup; deploy both Apps from the same checkout.

The [two-App benchmark](BENCHMARK_RESULTS.md) measured **2.23 → 5.44 req/s (2.44×)** at 16 users,
with zero failed or incomplete requests and 618 `OK` traces across all stages and preflights. The
same document also retains the older benchmark that changed one App's fixed count. A short
real-model run did not establish an App throughput gain because the shared model service became a
limit.

This demonstrates provisioned horizontal capacity. Neither setup includes a traffic-triggered
autoscaling policy. More Uvicorn workers are a separate within-instance setting; they share that
instance's CPU and memory. `DurableAgentServer` needs no scaling-specific code change.

## References

- [Horizontal scaling for Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/horizontal-scaling)
- [Agent Server and shared run state](https://docs.databricks.com/aws/en/agents/deploy/agent-server)
- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [AgentKit runtime architecture](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentkit/runtime/ARCHITECTURE.md)
