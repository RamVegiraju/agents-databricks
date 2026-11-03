# 03 · Load test a managed Agent Bricks agent

Deploy a real inventory assistant with `DurableAgentServer`, then load test its
`/api/invocations` endpoint with the published Agent Bricks CLI. The OpenAI Agents
SDK calls an existing Databricks model service and a read-only synthetic inventory
tool. No order or shipment is created.

## Before you start

You need Python 3.11+, `uv`, Databricks CLI 1.20+, permission to create an App and
use a `system.ai` model service, and managed Runtime Store support in the workspace.
The selected model must support chat completions and tool calls. The CLI and App
install packages from PyPI; use your package index if PyPI is unavailable.

## 1. Choose your workspace and model

Run these commands from the repository root in one terminal. Replace the three
example values with your own. The deployment name must be unique in the workspace
and contain at most 17 lowercase letters, digits, or hyphens.

```bash
cd pro-code/03-agent-load-test
databricks auth profiles
DBX_PROFILE='your-profile'
databricks ai-gateway list-model-services --parent schemas/system.ai --profile "$DBX_PROFILE" --output json
MODEL_SERVICE='system.ai.your-model'
DEPLOY_NAME='inventory-lt-demo'
APP_NAME="agent-bricks-$DEPLOY_NAME"
python3 scripts/select_model.py "$MODEL_SERVICE"
```

If you need a new profile, run
`databricks auth login --host <workspace-url> --profile <new-profile>` first.
Choose a listed model that supports
`mlflow/v1/chat/completions` and tool calls.

## 2. Install, check, and deploy

```bash
uv sync --default-index https://pypi.org/simple
uv sync --project cli --default-index https://pypi.org/simple
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" doctor .
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" --output json deploy "$DEPLOY_NAME" \
  --source . --instances 1 --pip-index-url https://pypi.org/simple/
```

Wait for `deploy` to report `ready: true`. It creates the App and its managed
Runtime Store, binds the existing model service, and grants the App identity access.
It does not create a model endpoint, Session Store, or Memory Store. Each inventory
request is independent. Model and App usage may incur charges.

## 3. Test the real agent and run the CLI for one minute

Use a fresh run name each time. The `mkdir` command creates both output parents;
`--save-responses` requires its parent directory to exist.

```bash
RUN_NAME='my-first-run'
mkdir -p "results/$RUN_NAME" "private/$RUN_NAME"
uv run --frozen python scripts/smoke.py "$DBX_PROFILE" "$APP_NAME" "private/$RUN_NAME/smoke.json"
uv run --frozen --project cli agentbricks --profile "$DBX_PROFILE" --output json \
  endpoint loadtest "$APP_NAME" \
  --path /api/invocations --requests requests.json --sse \
  --concurrency 2 --max-duration 60 --timeout 50 \
  --report-dir "results/$RUN_NAME/report" \
  --save-responses "private/$RUN_NAME/responses.json"
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
