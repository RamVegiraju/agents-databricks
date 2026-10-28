# 04 · Genie supervisor

Build a LangGraph supervisor that delegates to separate **sales** and **inventory** Genie Agents.
Each specialist queries its own data; the supervisor combines their evidence into an answer.

## Before you start

Complete the [shared setup](../../docs/GETTING_STARTED.md) and create the two Genie Agents using
[the lower-code sample](../../lower-code/genie-agents/README.md). Record their returned space IDs.
You need model access plus access to both agents, their warehouse, and underlying data.

```bash
cd pro-code/04-genie-supervisor
export PROFILE="my-workspace"
uv sync --frozen
uv run --frozen pytest -q
uv run --frozen python bind_genie.py \
  --sales-space-id 'YOUR_SALES_SPACE_ID' \
  --inventory-space-id 'YOUR_INVENTORY_SPACE_ID'
uv run --frozen agentbricks doctor .
```

The checked-in IDs are placeholders. Binding names `sales` and `inventory` must match the specialist
code. This is a custom Python supervisor, not a managed Supervisor resource.

## Run

```bash
uv run --frozen agentbricks --profile "$PROFILE" dev --app-port 8002
```

Open `http://localhost:8002`. Model and Genie calls are live; conversation state is local in `dev`.
To deploy with managed state:

```bash
export AGENT_NAME="genie-supervisor"
export APP_NAME="agent-bricks-$AGENT_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source .
databricks apps get "$APP_NAME" --profile "$PROFILE"
```

Open the returned App URL. Deployment reconciles Genie grants, but does not grant underlying Unity
Catalog data access. Grant the App's `service_principal_client_id` the required catalog/schema use
and table read privileges, and verify its warehouse access under the Genie security model.

## Try it

Use the synthetic data dates below, or replace them with dates in your own data.

| Question | Look for |
| --- | --- |
| “Which product had the highest net revenue October 1–3, 2026? Fetch the query rows.” | Sales specialist, executed SQL, and rows. |
| “Which product/warehouse pairs were below reorder point on October 3, 2026?” | Inventory specialist and a single snapshot date. |
| “Compare sales October 1–3 with October 3 stock. Which best-selling products need replenishment review?” | Both specialists and an answer grounded in both results. |

Inspect tool messages and **Traces**. Specialists use native Genie ask/poll/result tools; pending
queries must complete and rows must be fetched before their results are treated as evidence.
Each delegation starts a fresh specialist conversation, so the supervisor supplies relevant context.

Stop local execution with Ctrl+C, or stop the deployed App:

```bash
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "$APP_NAME" --yes
```

## Customize

| File | Purpose / what to change |
| --- | --- |
| [agent/supervisor.py](agent/supervisor.py) | Specialist domains, routing instructions, and answer synthesis. |
| [bind_genie.py](bind_genie.py) | Bind real space IDs without rewriting other configuration. |
| [agent/agent.py](agent/agent.py) | Model, native Genie tools, sessions, and tracing. |
| [agent.toml](agent.toml), [app.yaml](app.yaml) | Tool/store declarations and startup. |
| [../../lower-code/genie-agents/assets/](../../lower-code/genie-agents/assets/) | Domain context, questions, and reviewed SQL examples. |
| [runtime/](runtime/), [ui/](ui/), [tests/](tests/) | Invocation/state handling, browser UI, and offline checks. |
| [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Dependencies and generated lockfile. |

This sample uses a fixed demo actor; add verified identity and session ownership before multi-user
use. It does not record pipeline-readable transcripts or configure memory distillation; see
[02 · Agent memory](../02-agent-memory/README.md) for that capability.

See the [Genie API](https://docs.databricks.com/aws/en/genie-agents/conversation-api),
[shared validation record](../../docs/VALIDATION.md), and [runtime contract](AGENTKIT_CONTRACT.md).
