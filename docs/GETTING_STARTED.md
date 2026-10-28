# Getting started

## Requirements

- Python 3.11+, [uv](https://docs.astral.sh/uv/), and the [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install).
- Bash or Zsh. The invocation examples use `uuidgen`; install it if your system does not provide it.
- A Databricks workspace with model access. Deployment additionally needs Databricks Apps and permission to create the sample's declared resources.

The Python samples pin Agent Bricks 0.7.0. Run commands from the sample directory; each has its own environment.

## Authenticate

Choose your workspace and a profile name. Keep `PROFILE` set in each terminal:

```bash
export PROFILE="my-workspace"
databricks auth login --host 'https://YOUR_WORKSPACE_HOST' --profile "$PROFILE"
databricks auth profiles
```

Use an existing authenticated profile instead of signing in again when appropriate. Never commit credentials or `.env` files.

## Install and check a sample

From the repository root, enter the sample directory listed in its README:

```bash
uv sync --frozen
uv run --frozen agentbricks doctor .
uv run --frozen pytest -q
```

`doctor` checks configuration and wiring; tests check local behavior. Neither proves that remote tools or permissions work.
The lower-code project uses `uv sync --frozen --group dev` and does not need `doctor`.

## Local versus deployed

| Command | What runs |
| --- | --- |
| `uv run --frozen agentbricks --profile "$PROFILE" dev` | Local server; model/tool calls still reach Databricks. Managed memory is off; conversation state stays in process. |
| `uv run --frozen agentbricks --profile "$PROFILE" deploy NAME --source .` | Creates or updates `agent-bricks-NAME`, provisions declared resources/access, uploads source, and starts the App. |

Use a deployment name of at most 17 lowercase letters, digits, and hyphens. Reusing a name updates that App.
Open the returned URL for samples with a UI. Samples 01 and 05 use the invocation API.

A request needs a fresh invocation UUID (`id`) and a stable conversation ID (`session_id`). Reuse the conversation ID for follow-ups; change it for a new conversation.

If deployment outlasts your terminal's timeout, use `deploy ... --no-wait`, then
`deployments wait APP_NAME`. Exit 75 means wait again for the same deployment; do not start another one.

## Stop and restart

From the same sample directory:

```bash
export APP_NAME="agent-bricks-YOUR_DEPLOYMENT_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deployments get "$APP_NAME"
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "$APP_NAME" --yes
# Resume later without uploading code changes:
uv run --frozen agentbricks --profile "$PROFILE" deployments start "$APP_NAME"
```

Verify `compute_status.state` is `STOPPED` when finished. Stopping an App preserves its data and does not stop independent pipelines, warehouses, or search/Lakebase resources.
Apps, model/tool calls, pipeline runs, and backing services can incur charges. See [App compute](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/) and the chosen feature's documentation.

## Change the sample

| Files | Change here |
| --- | --- |
| `agent/` | Prompts, model, graph, and tools. |
| `agent.toml` | Tool and managed-store bindings. Review names and permissions for your workspace. |
| `app.yaml` | Startup and application environment. Deployment adds workspace-specific settings. |
| `runtime/` | Request translation, state, and recovery. Read the sample's `AGENTKIT_CONTRACT.md` before changing it. |
| `ui/` | Browser presentation, where included. |
| `tests/` | Representative behavior and failure cases. |
| `pyproject.toml`, `uv.lock` | Dependencies and generated lockfile. Regenerate the lockfile with uv after changing dependencies. |

`.venv/`, local traces, deployment state, rendered request files, and benchmark reports are generated output.
These demos use a fixed actor where managed state is enabled; add verified identity and session ownership before multi-user use.

## Help

Use `uv run --frozen agentbricks COMMAND --help` for installed options and
`deployments logs APP_NAME` for App logs. If a local port is occupied, use `dev --app-port 8002`.
See the [Agent Bricks CLI guide](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli) and [validation record](VALIDATION.md).
