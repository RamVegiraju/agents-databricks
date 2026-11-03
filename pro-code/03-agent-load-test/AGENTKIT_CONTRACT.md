# Managed runtime contract

`runtime/main.py` constructs `DurableAgentServer` and registers the `invoke` and
`recover` hooks in `runtime/adapter.py`. The framework-native OpenAI Agents SDK
agent remains in `agent/assistant.py`, with a read-only local tool in
`agent/tools.py`. The managed runtime owns invocation status, streaming transport,
result persistence, polling, and replay. Deployment provisions its Runtime Store.

`POST /api/invocations` accepts a client-generated UUID `id`, a top-level
`session_id`, `input: {"messages": [{"role": "user", "content": "..."}]}`, and an
optional `stream` boolean. The invocation ID is an idempotency key; use a fresh ID
for each measured request. The session ID groups calls but this sample has no
conversation history or long-term memory binding. Requests are independent.

The nonstreamed response is `{ "id": ..., "status": "completed", "output": {...} }`.
The output contains the answer, model, SDK usage, and actual inventory tool audit.
The streamed response emits `delta` answer-text events and a `run.completed`
event with usage. The load tester reads these for answer-text TTFT, output tokens,
and completion. The managed result can also be retrieved with
`GET /api/invocations/{id}`; `GET /api/invocations/{id}/events` replays events.

At most two agent calls run concurrently per App process. The 45-second deadline
includes waiting for a slot. Recovery may replay an interrupted invocation; the
only tool reads local synthetic inventory and has no external side effects.

The declared existing model service is injected as `AGENT_MODEL_SERVICE_AGENT`.
Local execution requires an explicit Databricks profile. The App uses its service
principal. The Agent Bricks OpenAI tracing adapter is initialized, but this sample
does not bind a workspace tracing experiment. The deployed App ingress enforces
authentication; localhost is for local development.
