# Sample agent transport and runtime contract

This project extends the Agent Bricks custom OpenAI/FastAPI server pattern. `app.yaml`
starts `app.py`. The framework-native agent is in `agent/assistant.py`, and its local
read-only tool is in `agent/tools.py`. Agent Bricks owns deployment and load generation;
FastAPI owns this sample's synchronous HTTP agent transport.

`POST /invocations` accepts one user message in `input` and an optional `stream` boolean.
`id` defaults to a UUID; `session_id` is optional correlation metadata. With streaming,
Responses-style SSE reports answer-text deltas and one final completion or failure event.
With `stream: false`, one JSON object includes the answer, actual tool audit, and native
SDK token usage. A complete HTTP exchange includes the full tool/model run.

There is no durable runtime, Session Store, Memory Store, database, or response replay.
Requests are independent. Credentials come from the explicit local profile or deployed
App identity. The declared existing model-service binding is injected by the deployment
as `AGENT_MODEL_SERVICE_AGENT`; local execution falls back to the same named service.
The server configures the native model client once at startup, off the event loop.

No tracing destination is declared or created. OpenAI-hosted tracing is disabled. Missing
trace IDs remain null in native loadtest exports. The deployed Databricks App ingress
enforces authentication; the localhost development server is for local use only.
