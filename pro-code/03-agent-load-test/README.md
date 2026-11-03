# 03 · Load test a managed Agent Bricks agent

Deploy a real inventory assistant with `DurableAgentServer`, then load test its
`/api/invocations` endpoint with the published Agent Bricks CLI. The OpenAI Agents
SDK calls an existing Databricks model service and a read-only synthetic inventory
tool. The model service is the **LLM behind the agent**; the App runs the agent
code and tool. No order or shipment is created.

This directory is a complete Agent Bricks example: the agent, inventory tool,
managed-server adapter, and request bodies are already wired together. The steps
below deploy **this included agent** from a fresh clone; `agentbricks init` and an
existing deployment are not needed. The first `deploy` creates the App. Running
it again with the same name updates that App. To test your own agent, see
[Use your own agent](#use-your-own-agent) after the example steps.

## Before you start

You need Python 3.11+, `uv`, Databricks CLI 1.20+, permission to create an App and
use a `system.ai` model service, and managed Runtime Store support in the workspace.
The selected model must support chat completions and tool calls. The CLI and App
install packages from PyPI; use your package index if PyPI is unavailable.

## 1. Choose a workspace and model for the included agent

Run these commands from the repository root in one terminal. Replace the three
example values with your own. The deployment name must be unique in the workspace
and contain at most 17 lowercase letters, digits, or hyphens.

```bash
# Enter the existing project and choose a profile for your target workspace.
cd pro-code/03-agent-load-test
databricks auth profiles
DBX_PROFILE='your-profile'

# List existing model services; choose one that supports chat and tool calls.
databricks ai-gateway list-model-services --parent schemas/system.ai --profile "$DBX_PROFILE" --output json
MODEL_SERVICE='system.ai.your-model'

# Set the model used by the agent and choose a unique App deployment name.
python3 scripts/select_model.py "$MODEL_SERVICE"
DEPLOY_NAME='inventory-lt-demo'
APP_NAME="agent-bricks-$DEPLOY_NAME"
```

If you need a new profile, run
`databricks auth login --host <workspace-url> --profile <new-profile>` first.
Choose a listed model that supports
`mlflow/v1/chat/completions` and tool calls. Listing services creates nothing;
`select_model.py` updates the model setting in `agent.toml`, `app.yaml`, and
`agent/assistant.py`. If the sample's default `system.ai.claude-haiku-4-5` is
available, you can skip the list and selection commands.

## 2. Install, check, and deploy the included agent

```bash
# Install the agent and CLI in separate local environments; each sync creates a uv.lock.
uv sync --default-index https://pypi.org/simple
uv sync --project cli --default-index https://pypi.org/simple

# Check project wiring locally. This does not deploy or call the model.
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" doctor .

# Create or update the App in the selected workspace; wait for it to answer.
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" --output json deploy "$DEPLOY_NAME" \
  --source . --instances 1 --pip-index-url https://pypi.org/simple/
```

Wait for `deploy` to report `ready: true`. It creates the App and its managed
Runtime Store, binds the existing model service, and grants the App identity access.
It does not create a model endpoint, Session Store, or Memory Store. Each inventory
request is independent. `--instances 1` starts one App instance;
`--pip-index-url` selects its package source. `--frozen` uses the lockfiles from
the two sync commands. Model and App usage may incur charges.

## 3. Test the included agent for one minute

Use a fresh run name each time. The `mkdir` command creates both output parents;
`--save-responses` requires its parent directory to exist.

```bash
# Create new local directories for reports and private response captures.
RUN_NAME='my-first-run'
mkdir -p "results/$RUN_NAME" "private/$RUN_NAME"

# Send one real invocation through the CLI and verify the inventory tool result.
uv run --frozen python scripts/smoke.py "$DBX_PROFILE" "$APP_NAME" "private/$RUN_NAME/smoke.json"

# Run Locust through the published CLI for a full minute; no request cap is set.
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" --output json \
  endpoint loadtest "$APP_NAME" \
  --path /api/invocations --requests requests.json --sse \
  --concurrency 2 --max-duration 60 --timeout 50 \
  --report-dir "results/$RUN_NAME/report" \
  --save-responses "private/$RUN_NAME/responses.json"

# Check counts, outputs, token coverage, and all three workload cases.
uv run --frozen python scripts/check_results.py \
  "results/$RUN_NAME/report/summary.json" "private/$RUN_NAME/responses.json"
```

Open `results/<run-name>/report/index.html` for the HTML report;
`summary.json` has counts, latency, answer-text TTFT, throughput, token usage,
and errors. The run dispatches for 60 seconds and then drains active requests.
The checker confirms all three prompts ran with unique invocation IDs and nonempty
answers. `private/` contains actual prompts and answers and is ignored by Git.

For a faster, ten-request check, run
`bash scripts/loadtest.sh "$DBX_PROFILE" "$APP_NAME" another-run`.

`agentbricks deploy` records the chosen name in `agent.toml` and may write
workspace-specific Runtime Store values into `app.yaml`. Remove those generated
values before committing the sample for use in another workspace. See
`AGENTKIT_CONTRACT.md` for the HTTP contract and `VALIDATION.md` for measured runs.

## Use your own agent

The load-test CLI sends HTTP requests to an **already deployed** agent. It does
not create your agent, register its tools, or configure its model. First build and
deploy your Agent Bricks project using its own agent code, tool bindings,
permissions, and model settings. If starting from scratch, use `agentbricks init`
as described in the Agent Bricks CLI documentation; this sample's `init` step is
already done.

To adapt this example, change these parts before using step 3:

| Change | Where |
| --- | --- |
| Agent behavior and tools | Replace `agent/assistant.py`, `agent/tools.py`, and sample inventory data if you are adapting this project. Declare any managed resources in `agent.toml`, connect them in the agent code, and deploy. The model-service selection commands above apply only to this example's `system.ai` model. |
| Requests | Edit `requests.json` to contain complete request bodies for your agent, including `"stream": true` if using SSE. For managed invocations, keep `"id": "{{request_id}}"` to avoid cached results; use `"session_id": "{{user_id}}"` when each simulated user needs a stable session. |
| Endpoint and load | Point `APP_NAME` and `--path` at your deployed endpoint. Use `--sse` only when its response streams SSE. Set concurrency, duration, and timeout to match the workload you want to measure. |
| Sample-specific checks | Update or skip `scripts/smoke.py` and `scripts/check_results.py`: they expect this inventory tool, exactly three cases, streamed answer text, and token usage. |

If you are adapting the managed-server code itself, also update the input and
output mapping in `runtime/adapter.py` and document the new contract in
`AGENTKIT_CONTRACT.md`. For a separately deployed agent, skip this sample's
model selection, agent install, doctor, and deploy. Install only the CLI environment
with `uv sync --project cli --default-index https://pypi.org/simple`, prepare your
request file, and run the `endpoint loadtest` command from step 3 with your App
name and path.
