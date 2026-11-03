# Validation record — November 2, 2026

The metrics below came from the original sample directory before it was added to this
repository. Raw reports and response captures remain private because they include
workspace host details and actual prompts and answers. The published commands are in
`README.md` and use values selected in each target workspace.

## Repository and source checks

After copying the sample into this repository, `bash scripts/validate.sh` passed for
all seven pro-code samples, the lower-code assets, and the scaling runner. Sample 03
passed three inventory tests, Ruff lint, and Ruff format checks. The installed
`databricks-agentbricks[loadtest]==0.8.0` help accepted the documented flags.

The Agent Bricks source at `databricks/databricks-ai-bridge` commit
`4a0225a6aa15024a9848468f3ab6882a8de49b58` was checked for the published
CLI contract. Its loadtest implementation cycles request bodies, expands
`{{request_id}}` and `{{user_id}}`, excludes one warm-up, drains active requests
after the dispatch cap, and recognizes `response.completed` and answer-text
deltas in SSE. Its deployment code binds an existing model service, injects
`AGENT_MODEL_SERVICE_AGENT`, grants the App identity access, and accepts a custom
server. Its doctor checks specifically require the managed server. This source
is on `main` at version `0.9.0.dev0`; the live runs use the released 0.8.0 CLI.

## Deployed from this repository copy

The copied sample was deployed as `agent-bricks-lt-pro-1102` in the same staging
workspace, using `system.ai.claude-haiku-4-5` and one Medium App instance. The
deployment completed, the App was `RUNNING`, and the CLI reported the model grant
to the App service principal. A JSON smoke request completed with two real model
calls and one `check_inventory` tool call. Its MX-100 answer correctly split eight
units from Boston and ten from Chicago, with ten units missing the one-day deadline.

| Repository-copy run | Measured successes | Mean completion | p95 completion | Mean answer TTFT | Successful RPS | Output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bash scripts/loadtest.sh` | 10/10 | 2.79 s | 3.20 s | 1.76 s | 0.701 | 2177 |
| Direct `agentbricks endpoint loadtest` | 3/3 | 2.83 s | 3.00 s | 1.80 s | 0.547 | 657 |

Both runs had zero failures or incomplete requests, full answer-TTFT and token
coverage, and all three workload cases. The wrapper's case counts were 4/3/3;
the direct CLI run's were 1/1/1. Both response exports passed
`scripts/check_results.py`. One representative answer per case was inspected:
MX-100 missed its one-day deadline for ten units; SF-200 used a feasible
Chicago/Phoenix split; RX-300 had only five units and a seven-unit shortage.
Each run sent one additional excluded real warm-up request. The smoke and two
load runs made **16 total agent invocations** from the repository copy.

Private reports and responses remain in this checkout under `results/` and
`private/`; they are excluded from Git. The new App is left running so the user
can repeat the CLI commands. Its compute can be stopped with the command in
`README.md` afterward.

## Live tests completed

The original source was tested locally and as a hosted App in the shared staging workspace
with the explicitly selected `e2-dogfood-staging` profile and bounded traffic. Workspace identity was verified as
`ram.vegiraju@databricks.com`; workspace ID is `6051921418418893`.

- Workspace: https://e2-dogfood.staging.cloud.databricks.com
- Model: `system.ai.claude-haiku-4-5`, verified in the workspace and exercised with real inference.
- Agent: OpenAI Agents SDK `0.20.0`, read-only local inventory tool, synthetic inventory.
- Local target: `http://127.0.0.1:8766/invocations`; process stopped after capture.
- Hosted App: [https://agent-bricks-lt-ram-1102-6051921418418893.staging.aws.databricksapps.com](https://agent-bricks-lt-ram-1102-6051921418418893.staging.aws.databricksapps.com/docs).
- App management: https://e2-dogfood.staging.cloud.databricks.com/apps/agent-bricks-lt-ram-1102
- One Medium App instance, one process, two active invocations maximum.
- Hosted model authentication: App service principal; deploy granted model access.
- Native runner: `databricks-agentbricks[loadtest]==0.8.0`, Locust `2.47.0`.
- No stubbed model responses, fake agents, or substitute hosting were used.

## Measured results

| Target | Measured successes | Mean completion | p95 completion | Mean answer TTFT | Successful RPS | Output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| Local process | 8/8 | 3.50 s | 4.00 s | 2.38 s | 0.554 | 1746 |
| Databricks App | 10/10 | 3.18 s | 4.80 s | 2.00 s | 0.622 | 2109 |

Both runs observed peak concurrency **2**, zero measured failures and zero incomplete
requests. Answer-text TTFT and output-token usage coverage are complete for every measured
success. Local elapsed time including drain: 14.45 s;
hosted: 16.08 s. Percentiles are the native Locust
histogram estimates. TTFT means the first nonempty answer-text delta, including the model/tool
work that precedes the answer; it is not the initial SSE event.

These are small bounded runs of the complete agent/model/tool path. They do not establish
sustainable capacity, isolate hosting overhead, or constitute a scored quality evaluation.

## Traffic accounting and findings

Local used **11 agent attempts total**: two initial failed diagnostics, one successful JSON
smoke, eight successful measured streaming requests, no warm-up. The first HTTP invocation
and a direct SDK diagnostic both hit the provider with an unsupported optional
`parallel_tool_calls` field. Provider response: `BAD_REQUEST`,
`parallel_tool_calls: Extra inputs are not permitted`. Removing that field fixed execution;
the measured cap was reduced to eight to preserve the approved total. The diagnostic was
a real provider attempt, not a successful inference result.

Hosted used **12 agent invocations total**: one successful JSON smoke, one successful
excluded warm-up, ten successful measured streaming requests. Build and health checks did
not invoke the agent. The measured report excludes smoke, warm-up, and the local diagnostics.
No retries were enabled at the provider; each invocation allowed at most three model turns
and 384 output tokens per turn. Both smoke audits show exactly two model calls and one actual
`check_inventory` execution.

Inspected one captured answer per case in each load run, plus both smoke audits:

- MX-100/Boston: eight units from Boston at one business day and ten from Chicago at two;
  ten miss the requested one-day deadline.
- SF-200/Austin: feasible fifteen-unit split across Chicago and Phoenix within two business days.
- RX-300/Boston: only five available across all warehouses; shortfall seven.

These manual checks are limited to the inspected responses. The server requires an actual
tool execution for every successful invocation; the native loadtest export captures answers
but does not preserve the terminal tool audit or model-request count for every measured run.
No stock was reserved and no order or shipment was created.

## Commands run

From the original sample directory, before it was copied into `pro-code/03-agent-load-test`:

```sh
DATABRICKS_CONFIG_PROFILE=e2-dogfood-staging .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8766
cli/.venv/bin/agentbricks --profile e2-dogfood-staging --output json endpoint invoke --url http://127.0.0.1:8766 --path /invocations --no-auth --timeout 50 --json '<MX-100 smoke body in private evidence>'
cli/.venv/bin/agentbricks --profile e2-dogfood-staging --output json endpoint loadtest --url http://127.0.0.1:8766 --no-auth --path /invocations --requests requests.json --sse --concurrency 2 --max-duration 60 --max-requests 8 --timeout 50 --no-warmup --report-dir results/local-20261102/report --save-responses private/local-20261102/responses.json
.venv/bin/python scripts/check_results.py results/local-20261102/report/summary.json private/local-20261102/responses.json
cli/.venv/bin/agentbricks --profile e2-dogfood-staging deploy lt-ram-1102 --source . --instances 1 --pip-index-url https://pypi.org/simple/
.venv/bin/python scripts/smoke.py e2-dogfood-staging agent-bricks-lt-ram-1102 private/hosted-20261102/smoke.json
bash scripts/loadtest.sh e2-dogfood-staging agent-bricks-lt-ram-1102 hosted-load-20261102
databricks apps stop agent-bricks-lt-ram-1102 --profile e2-dogfood-staging
```

Both response-export consistency checks passed: counts agree, unique invocation identities,
two user identities, all three cases, nonempty answers, complete TTFT and output-token coverage.
The local case counts are 3/3/2; hosted counts are 4/3/3.

## Artifacts and cleanup

- Local report: `results/local-20261102/report/index.html`; native JSON, Locust HTML and CSV alongside it.
- Hosted report: `results/hosted-load-20261102/report/index.html`; same native formats.
- Private real inputs/answers: `private/local-20261102/responses.json` and
  `private/hosted-load-20261102/responses.json`, mode 0600.
- Complete JSON smoke answers, usage and actual tool audits:
  `private/local-20261102/smoke-fixed.json` and `private/hosted-20261102/smoke.json`.
- Verified final App compute status **STOPPED**, retained in
  `results/hosted-load-20261102/app-stopped.json`. The App URL is retained but cannot serve
  requests until the App is restarted. Source and model grant remain for review/reuse.

## Setup checks and compatibility

- Pure inventory tool tests: three passed, no model calls and no provider stubs.
- Ruff check and format check: passed, including after the provider compatibility fix.
- FastAPI OpenAPI export, request schema and native tool schema checked without inference.
- Native `doctor` reported 3/8 onboarding checks passed: it requires the managed
  `DurableAgentServer` template and the corresponding adapter/dependency. This custom
  FastAPI server deployed and answered successfully; doctor is not a custom-server gate.
- First hosted build failed because the builder could not reach
  `pypi-proxy.cloud.databricks.com`. The retry used public PyPI with the locked version pins
  in requirements.txt and succeeded. Local lockfiles retain their actual mirror provenance.
- CLI 1.20's DAB schema rejects MODEL_SERVICE App resources, so the sample uses native
  Agent Bricks deployment and the supported manifest model binding.
- No MLflow or OpenAI trace destination was configured; exported trace IDs are null.
  No persistence, memory, production authentication policy, autoscaling, saturation, or
  long-duration capacity behavior was tested.
