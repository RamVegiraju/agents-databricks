# 06 · Retail assistant

Combine a retail Genie Agent, policy retrieval, and optional GitHub MCP in one browser assistant.

| Question | Source | Evidence to inspect |
| --- | --- | --- |
| Sales or stock | Curated Genie Agent | Executed SQL and query rows. |
| Returns, shipping, replenishment | AI Search over policy documents | Retrieved passage, source URI, and chunk ID. |
| Repository implementation | Optional GitHub MCP | File content and repository links. |

## Before you start

Complete the [shared setup](../../docs/GETTING_STARTED.md).
You need a combined retail Genie Agent, a ready policy search index, and their access grants.
GitHub is optional and requires a separately supplied credential.

```bash
cd pro-code/06-retail-assistant
export PROFILE="my-workspace"
uv sync --frozen
uv run --frozen pytest -q
uv run --frozen agentbricks doctor .
```

Follow [resource setup](SETUP.md) before running the agent.
Setup scripts preview changes by default; `--apply` contacts the workspace and creates resources.
App startup does not provision these integrations.

## Run

After resource setup, set your actual index and start locally:

```bash
export POLICY_INDEX_NAME="YOUR_CATALOG.YOUR_SCHEMA.policy_index"
uv run --frozen agentbricks --profile "$PROFILE" dev
```

Open `http://localhost:8000`. Model and tool calls are live; managed memory is disabled in local
`dev`. Stop with Ctrl+C.

For a deployed App, set `POLICY_INDEX_NAME` in `app.yaml` to your actual index, preserving the other settings:

```yaml
env:
  - name: POLICY_INDEX_NAME
    value: YOUR_CATALOG.YOUR_SCHEMA.policy_index
```

```bash
export AGENT_NAME="retail-demo"
export APP_NAME="agent-bricks-$AGENT_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source .
uv run --frozen python -m scripts.grant_app_access \
  --profile "$PROFILE" --app "$APP_NAME" --schema YOUR_CATALOG.YOUR_SCHEMA
# Review the preview, then grant access:
uv run --frozen python -m scripts.grant_app_access \
  --profile "$PROFILE" --app "$APP_NAME" --schema YOUR_CATALOG.YOUR_SCHEMA --apply
```

Open the returned App URL. The grant helper expects `sales`, `inventory`, and `policy_index` in the
chosen schema. It preserves other App resources. Run it again after deployment if those resources change.

## Try it

| Ask | Look for |
| --- | --- |
| “Which product had the highest net revenue October 1–3, 2026? Fetch the query rows.” | Genie ask/poll/result calls and rows. |
| “Can a Rain Shell be returned after 20 days?” | Policy search and a passage citation. |
| “Which products need replenishment review on October 3, 2026? Use sales October 1–3 and the replenishment policy.” | Both tabular and policy evidence. |
| “Read README.md from owner/repository using GitHub and explain the ingestion approach.” | A real MCP file read; requires the optional setup and an authorized repository. |

Inspect tool request/results and **Traces**, not just the final answer. Pending Genie queries must
finish and query rows must be fetched. GitHub MCP requires live credential validation in your workspace.

```bash
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "$APP_NAME" --yes
```

Stopping the App does not stop search, warehouse, or backing storage resources.

## Customize

| File | Purpose / what to change |
| --- | --- |
| [agent/prompt.py](agent/prompt.py) | Source routing, business context, and citation rules. |
| [agent/tools/policy_search.py](agent/tools/policy_search.py) | Hybrid retrieval and result decoding. |
| [data/policies/](data/policies/) | Replace synthetic policies with approved documents. |
| [scripts/ingest_policies.py](scripts/ingest_policies.py), [scripts/create_search_index.py](scripts/create_search_index.py) | Document chunking, ingestion, and search-index lifecycle. |
| [scripts/register_mcp.py](scripts/register_mcp.py) | Optional governed GitHub connection and service. |
| [scripts/grant_app_access.py](scripts/grant_app_access.py) | App access to the source tables and index. |
| [agent/agent.py](agent/agent.py), [agent.toml](agent.toml), [app.yaml](app.yaml) | Agent composition, active bindings, and startup. |
| [resources/agent.bindings.toml.example](resources/agent.bindings.toml.example) | Inactive binding example; changes here do not configure the App. |
| [runtime/](runtime/), [ui/](ui/), [tests/](tests/) | Runtime contract, browser UI, and checks. |
| [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Dependencies and generated lockfile. |

Add verified identity and session ownership before multi-user use. For transcript extraction and
cross-session memory, see [02 · Agent memory](../02-agent-memory/README.md); checkpoint data alone
is not a readable transcript.

See [AI Search](https://docs.databricks.com/aws/en/ai-search/create-ai-search),
[MCP registration](https://docs.databricks.com/aws/en/ai-gateway/register-mcp-service),
[validation evidence](../../docs/VALIDATION.md), and [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md).
