# 03 · Load test a real agent

This sample deploys an inventory assistant to Databricks Apps, then uses the published
`databricks-agentbricks[loadtest]==0.8.0` CLI to measure its `/invocations` endpoint.
The OpenAI Agents SDK calls a **real Databricks model service** and a read-only local
inventory tool. Stock is synthetic; the agent never places an order.

## What you need

- Python 3.11+, `uv`, and Databricks CLI 1.20+
- A Databricks CLI profile that you explicitly choose for the target workspace
- Permission to create an App and use an existing `system.ai` chat model service

Run from the repository root. Replace `<profile>`, `<model-service>`, and `<name>` with
values from **your** workspace. The deployment name must be unique in that workspace,
with at most 17 lowercase letters, digits, or hyphens.

```bash
cd pro-code/03-agent-load-test
databricks auth profiles
databricks ai-gateway list-model-services --parent schemas/system.ai --profile <profile> --output json
python3 scripts/select_model.py <model-service>
uv sync --default-index https://pypi.org/simple
uv sync --project cli --default-index https://pypi.org/simple
uv run --project cli agentbricks --profile <profile> deploy <name> \
  --source . --instances 1 --pip-index-url https://pypi.org/simple/
```

Choose a listed service supporting `mlflow/v1/chat/completions` and tool calls.
For example, `<model-service>` might be `system.ai.claude-haiku-4-5` if your
workspace exposes it. `select_model.py` updates the model binding, App environment,
and local fallback together. The deploy command creates `agent-bricks-<name>`;
use that as `<app-name>` below. It binds the existing model service and grants
the App identity access. No separate model endpoint, database, or store is created.
Package installation requires access to public PyPI. The CLI and App use separate
Python environments. Local `uv.lock` files are generated during `uv sync` and are
not committed because the original validation environment used an internal mirror.

## Run your own end-to-end test

The smoke command sends one real request and verifies the actual inventory tool
result. The load test sends one warm-up and up to ten measured requests, at most two
at a time. A run can continue past the 60-second dispatch limit while active
requests finish. The sample agent limits each request to three model turns and
384 output tokens per turn. Model and App charges apply.

```bash
mkdir -p private
uv run python scripts/smoke.py <profile> agent-bricks-<name> private/smoke.json
bash scripts/loadtest.sh <profile> agent-bricks-<name> my-first-run
```

To run the published CLI directly instead of the wrapper, use a **new** run name:

```bash
mkdir -p results/my-cli-run private/my-cli-run
uv run --project cli agentbricks --profile <profile> --output json \
  endpoint loadtest agent-bricks-<name> \
  --path /invocations --requests requests.json --sse \
  --concurrency 2 --max-duration 60 --max-requests 10 --timeout 50 \
  --report-dir results/my-cli-run/report \
  --save-responses private/my-cli-run/responses.json
uv run python scripts/check_results.py \
  results/my-cli-run/report/summary.json private/my-cli-run/responses.json
```

Open `results/my-first-run/report/index.html` (or `my-cli-run`) for the native
HTML report. `summary.json` contains request counts, latency, answer-text time
to first token, throughput, token usage, and errors. `check_results.py` verifies
that the summary and captured responses agree and that all three workload cases
were exercised. The private directory contains actual prompts and answers; do not
commit it. Use a fresh run name and smoke filename each time.

When finished, stop App compute while retaining the deployment:

```bash
databricks apps stop agent-bricks-<name> --profile <profile>
```

## What is tested

The three prompts ask for a shipment of MX-100 to Boston, SF-200 to Austin, and
RX-300 to Boston. The inventory tool subtracts reservations and returns stock by
warehouse and estimated transit days. The agent must explain a missed deadline,
a feasible split, or a shortage. `SAMPLE_OUTPUT.md` shows a recorded response.
`VALIDATION.md` records the real local and hosted runs in the staging workspace.
These short runs verify the full path; they do not establish sustained capacity.

For local development, set `DATABRICKS_CONFIG_PROFILE=<profile>` explicitly and run
`uv run uvicorn app:app --host 127.0.0.1 --port 8766`. The local server also calls
the real workspace model and has no ingress authentication. Offline checks are
`uv run ruff check .`, `uv run ruff format --check .`, and `uv run python -m pytest -q`.

`agentbricks doctor` checks managed-server onboarding and reports this custom
FastAPI server as not onboarded. The custom server is supported by the native
deploy, invoke, and loadtest paths demonstrated here.
