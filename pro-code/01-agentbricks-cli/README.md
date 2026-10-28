# 01 · Agent Bricks CLI quickstart

Run a LangGraph agent with one Python `get_current_time` tool locally, then deploy it to
Databricks Apps. This checked-in sample exposes an API, with no browser chat UI, managed
Session Store, Memory Store, or external tool. Its deployed Runtime Store preserves invocation
records; conversation checkpoints stay in process memory and are lost on restart.

## What the CLI provides

Agent Bricks supplies project templates, local development commands, and deployment/resource
provisioning. Its installed AgentKit package supplies `DurableAgentServer`, a FastAPI-based server
with invocation, status, streaming, and recovery infrastructure. This sample supplies the clock
tool, model/prompt, LangGraph loop, and handlers that connect the graph to that server.

To see the default CLI scaffold, run this **separately from the sample** in a directory where
`my-agent` does not exist:

```bash
uvx --from databricks-agentbricks==0.7.0 agentbricks init --framework langgraph my-agent
```

`uvx --from` runs the pinned CLI without a global installation. `init` creates a new project;
the default LangGraph template includes a chat UI and declared session/memory stores. It does
not deploy an App. The commands below use this repo's smaller sample, so no `init` is needed.

## 1. Prerequisites and authentication

Use Python 3.11+, [uv](https://docs.astral.sh/uv/), the
[Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install), and a workspace with
access to `system.ai.claude-sonnet-4-5`. Change `MODEL` in [agent/agent.py](agent/agent.py) if
you need another supported model. The examples use Bash/Zsh and `uuidgen` to generate IDs
(available on macOS; install it on Linux if missing). `jq` is optional for the compact display below.

From the repository root:

```bash
cd pro-code/01-agentbricks-cli

# Replace these values with your workspace URL and chosen profile name.
WORKSPACE_URL="https://<your-workspace-url>"
PROFILE="my-workspace"

databricks auth login --host "$WORKSPACE_URL" --profile "$PROFILE"
databricks auth profiles
```

| Command | What it does |
| --- | --- |
| `databricks auth login` | Opens browser-based OAuth sign-in and saves a named workspace profile. Run again if credentials expire. |
| `databricks auth profiles` | Lists configured profiles, workspace hosts, and credential validity. Confirm the intended workspace. |

Keep `PROFILE` set in each terminal. These examples pass Agent Bricks' global `--profile` before
the subcommand, so no separate `agentbricks login` is required. That command is an alternative
for validating a profile and remembering it as the CLI default.

## 2. Install and check the sample

```bash
uv sync --frozen
uv run --frozen agentbricks --version
uv run --frozen agentbricks doctor .
uv run --frozen pytest -q
```

| Command | What it does |
| --- | --- |
| `uv sync --frozen` | Creates/updates `.venv` from the checked-in `uv.lock`, including the project and default development dependencies, without updating the lockfile. |
| `uv run --frozen …` | Runs a command in that project environment using the existing lockfile. The sample pins Agent Bricks CLI 0.7.0. |
| `agentbricks --version` | Prints the installed CLI version. |
| `agentbricks doctor .` | Reads configuration and Python source to check onboarding: manifest, server choice, scaffold metadata, dependency declaration, startup command, server/handler wiring, framework integration, and deployment name. It does not execute the agent or verify workspace access. |
| `pytest -q` | Runs two offline tests: the graph's clock-tool loop with a fake model, and the server's invocation routes. It does not call a workspace model. |

A passing `doctor` confirms static wiring. The live requests below check actual model and tool execution.

## 3. Run and invoke locally

In terminal 1, from this sample directory with `PROFILE` set:

```bash
uv run --frozen agentbricks --profile "$PROFILE" dev
```

`dev` runs the startup command from `app.yaml`, using your profile to call Databricks model serving.
It serves this sample at `http://localhost:8000`, keeps invocation/conversation state in process
memory, and starts local MLflow tracing under `.agentbricks/`. Open the printed Traces URL to inspect
the run. It does not deploy an App or provision managed session/memory stores. Stop it with Ctrl+C.

In terminal 2, from the repository root:

```bash
cd pro-code/01-agentbricks-cli
PROFILE="my-workspace"  # Use the same profile as terminal 1.

uv run --frozen agentbricks --profile "$PROFILE" endpoint invoke \
  --url http://localhost:8000 \
  --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"demo-local\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Use your tool to tell me the UTC time.\"}]},\"stream\":false}"
```

`endpoint invoke` sends one HTTP request. `--url` selects the local server, `--path` selects its
invocation endpoint, and `--json` supplies the request body. For this adapter:

| Field | Meaning |
| --- | --- |
| `id` | A new UUID for each invocation; `uuidgen` generates it on every command run. Reusing an ID can return the existing invocation rather than run the clock again. |
| `session_id` | A nonempty conversation ID. Reuse it for related turns, with a new invocation `id` each time. It does not make conversation history durable. |
| `input.messages` | The role/content messages passed into LangGraph. This sample requires an object containing a `messages` list. |
| `stream: false` | Waits for the completed JSON response instead of requesting an SSE stream. |

Success means top-level `status` is `completed`, `output.output` includes a successful
`get_current_time` tool message, and the final assistant message uses its timestamp. HTTP success
alone does not establish that the tool ran.

For a compact demo display, append this pipe to the last line of either invocation command,
before pressing Enter (requires `jq`):

```text
| jq '{status, tool_results: [.output.output[] | select(.type == "tool") | {name, status, content}], answer: .output.output[-1].content}'
```

## 4. Deploy and invoke on Databricks Apps

Local `dev` is optional for deployment. Stop the local server when finished, then run these from
the sample directory with `PROFILE` set. Choose a unique name for a new App; names can use up to
17 lowercase letters, digits, and hyphens because the CLI adds `agent-bricks-`.

```bash
AGENT_NAME="cli-quickstart"  # Change for an isolated deployment.

uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source .
uv run --frozen agentbricks --profile "$PROFILE" deployments get "agent-bricks-$AGENT_NAME"

uv run --frozen agentbricks --profile "$PROFILE" endpoint invoke "agent-bricks-$AGENT_NAME" \
  --path /api/invocations \
  --json "{\"id\":\"$(uuidgen)\",\"session_id\":\"demo-deployed\",\"input\":{\"messages\":[{\"role\":\"user\",\"content\":\"Use your tool to tell me the UTC time.\"}]},\"stream\":false}"
```

| Command | What it does |
| --- | --- |
| `deploy "$AGENT_NAME" --source .` | Creates or updates `agent-bricks-$AGENT_NAME`, reconciles declared resources and access, provisions its Runtime Store, uploads the source, and deploys/starts the App. Returns the hosted URL. No separate `bundle run` is needed. |
| `deployments get` | Reads the named App's status and URL; it does not invoke the agent. |
| `endpoint invoke <app-name>` | Resolves the App URL and authenticates the request with workspace OAuth. The deployed model call uses the App's identity. |

The first deploy can take a few minutes. The CLI records the deployment name in `agent.toml`
and writes runtime connection settings into `app.yaml`. Reusing the name updates that App; a later
`deploy` without a name uses the recorded name. Treat generated runtime settings as deployment
output rather than copying them between workspaces.

Local `--frozen` commands use the checked-in lockfile. In CLI 0.7.0, deployment source sync excludes
`uv.lock` and `.agentbricks/`; the App's `uv run start-server` installs from `pyproject.toml`.
This sample has no bound workspace tracing experiment; local dev traces do not prove deployed
trace visibility. See [Part 2](../02-agent-memory/README.md) for managed session/memory behavior.

For a terminal or automation with a short timeout, use these **instead of** the foreground deploy:

```bash
uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source . --no-wait
uv run --frozen agentbricks --profile "$PROFILE" deployments wait "agent-bricks-$AGENT_NAME"
```

`--no-wait` starts deployment in the background. `deployments wait` follows it: exit 0 means running,
1 means failed, and 75 means still deploying after the wait timeout; repeat the wait command.
Do not start another deploy while the first is running.

## 5. Logs, stop, and resume

Run these from the same terminal with `PROFILE` and `AGENT_NAME` set:

```bash
# Stream App logs; Ctrl+C ends log viewing.
uv run --frozen agentbricks --profile "$PROFILE" deployments logs "agent-bricks-$AGENT_NAME"

# Stop App compute after the demo; preserve the App, source, and Runtime Store.
uv run --frozen agentbricks --profile "$PROFILE" deployments stop "agent-bricks-$AGENT_NAME" --yes

# On a later run, start the existing deployment without uploading code changes.
uv run --frozen agentbricks --profile "$PROFILE" deployments start "agent-bricks-$AGENT_NAME"
```

`--yes` skips the stop confirmation. Use `deploy` again when code changes need uploading.
Stopping App compute does not delete its backing data resources.

## Repository structure and adaptation

Start with the clock tool and graph to understand the smallest API-only agent. For your own use case, replace the tool and prompt first, then choose deployment bindings. Read the runtime contract before changing request shapes or recovery.

| File or directory | Role in this demo | Adapt for your own agent |
| --- | --- | --- |
| [agent/tools/sample_tool.py](agent/tools/sample_tool.py) | The local UTC clock used to prove a real tool call. | Replace it with your domain operation; define useful tool arguments and results. |
| [agent/agent.py](agent/agent.py) | Model, instructions, tool binding, and the model → tool → model graph. | Change the model and instructions; adjust graph control flow only when the task needs it. |
| [agent/tools/__init__.py](agent/tools/__init__.py) | Discovers the local tool modules. | Keep registration consistent when adding or removing tool modules. |
| [agent.toml](agent.toml) | Framework/server, deployment name, and optional managed bindings. | Choose your App name and required resources. This sample currently has no managed conversation or memory binding. |
| [runtime/adapter.py](runtime/adapter.py) | Maps input messages and session IDs to graph runs and output events. | Edit for a different input/output contract; preserve invocation IDs and recovery behavior. |
| [runtime/main.py](runtime/main.py) | Constructs and starts DurableAgentServer. | Usually retain; extend server startup only when required. |
| [app.yaml](app.yaml) | Startup command; deployment adds environment settings. | Set application configuration; regenerate deployment-specific settings in the target workspace. |
| [pyproject.toml](pyproject.toml) | Dependencies and start-server entry point. | Add dependencies for your domain tools. |
| [uv.lock](uv.lock) | Generated dependency lockfile for local frozen commands. | Regenerate with uv after intentional dependency changes; do not hand-edit. |
| [tests/](tests/) | Offline clock-loop and HTTP-route checks. | Replace clock expectations with representative tool behavior and failure cases. |
| [AGENTKIT_CONTRACT.md](AGENTKIT_CONTRACT.md) | Invocation, checkpoint, and recovery integration requirements. | Consult before editing runtime integration. |
| [.agentbricks/](.agentbricks/) | Scaffold provenance plus generated local traces/deployment state. | Keep provenance; treat local run output as generated, not application logic. |

## Troubleshooting and references

- If an older `.venv` reports `Failed to spawn: start-server`, run
  `uv sync --frozen --reinstall-package agentbricks-cli-quickstart` and retry `dev`.
- If port 8000 is occupied, stop the previous server or use `dev --app-port 8002` and invoke
  `http://localhost:8002`.
- If your shell points `UV_INDEX_URL` at another registry, retain `--frozen` for this public-PyPI
  lockfile; avoid committing a registry-only lockfile rewrite from `uv sync --locked`.
- Inspect the exact installed options with `uv run --frozen agentbricks <command> --help`.

Commands and wiring were checked on **2026-10-27** against installed Agent Bricks CLI **0.7.0**, the
[Databricks guide](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli),
[upstream CLI README](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/README.md),
and CLI source for [doctor](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentbricks/cli/doctor.py),
[dev](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentbricks/cli/dev.py),
[deployment](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentbricks/cli/deploy.py),
and [invocation](https://github.com/databricks/databricks-ai-bridge/blob/main/integrations/agentbricks/src/databricks_agentbricks/cli/endpoint.py).
The uv flags follow its [locking and syncing documentation](https://docs.astral.sh/uv/concepts/projects/sync/).
Upstream `main` can change independently of this sample's pinned release.
