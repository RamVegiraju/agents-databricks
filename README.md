# Agents on Databricks

Independent Agent Bricks examples:

| Sample | What it shows |
| --- | --- |
| [Agent Bricks CLI quickstart](pro-code/01-agentbricks-cli/README.md) | Run a LangGraph clock agent locally, then deploy it to Apps |
| [Agent memory](pro-code/02-agent-memory/README.md) | Persist sessions, distill memories asynchronously, and recall them across conversations |
| [App scale-out](pro-code/03-horizontal-scaling/README.md) | One versus three fixed App instances, compared with Locust |
| [Genie supervisor](pro-code/04-genie-supervisor/README.md) | Delegation across Genie agents |
| [MCP server](pro-code/05-mcp-server/README.md) | Add a remote MCP tool to an agent |
| [Retail assistant](pro-code/06-retail-assistant/README.md) | Advanced combined Genie, AI Search, and optional GitHub MCP example |
| [Lower-code Genie Agents](lower-code/genie-agents/README.md) | Curated Genie definitions and synthetic data |

Each sample has its own setup instructions. Python samples require Python 3.11+ and
[uv](https://docs.astral.sh/uv/). Run `bash scripts/validate.sh` for local checks; uv may download
packages from the public index. The [validation record](docs/VALIDATION.md) summarizes checks.

## Repository structure and starting points

Each sample is an independent project with its own dependencies and deployment. Open its README
for the file-purpose/adaptation table and run commands from that sample's directory.

| Path | Purpose | Start here when adapting |
| --- | --- | --- |
| [pro-code/01-agentbricks-cli/](pro-code/01-agentbricks-cli/) | Minimal API-only graph and local Python tool. | Tool implementation and agent prompt/model. |
| [pro-code/02-agent-memory/](pro-code/02-agent-memory/) | Session persistence, asynchronous distillation, and cross-session recall. | Transcript recording, extraction instructions, actor identity, and store configuration. |
| [pro-code/03-horizontal-scaling/](pro-code/03-horizontal-scaling/) | Fixed-instance comparison with a separate Locust project. | Workload model, request mix, concurrency, and comparison runner. |
| [pro-code/04-genie-supervisor/](pro-code/04-genie-supervisor/) | Supervisor over two curated Genie domains. | Specialist routing/prompts and real Genie bindings. |
| [pro-code/05-mcp-server/](pro-code/05-mcp-server/) | Client agent using a managed MCP service. | Service binding, auth model, and tool-use instructions. |
| [pro-code/06-retail-assistant/](pro-code/06-retail-assistant/) | Genie, policy retrieval, and optional external MCP. | Source-routing prompt, documents/retrieval, and integration setup. |
| [lower-code/genie-agents/](lower-code/genie-agents/) | Curated Genie configuration, fixture SQL, and offline renderers. | Business definitions, SQL examples, and data/column context. |
| [scripts/validate.sh](scripts/validate.sh) | Runs each project's offline checks in its own environment. | Use after changes; inspect its scope before running. |
| [docs/VALIDATION.md](docs/VALIDATION.md) | Repository validation evidence. | Distinguish observed live results from local checks. |

For a custom agent, iterate on prompts, domain tools/data, and manifest bindings first. The `runtime/`
files implement the invocation/state/recovery contract; change them when your client or identity
integration requires it, using each sample's `AGENTKIT_CONTRACT.md`. UI files control presentation.
`uv.lock` is generated dependency output; `.venv`, local tracing/deployment state, benchmark reports,
and rendered SQL/request files are generated artifacts. Deployment can write workspace-specific
settings to `app.yaml`; regenerate those in the intended workspace rather than copying identities.
