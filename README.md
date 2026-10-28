# Agents on Databricks

Learn to build, deploy, and extend agents with Agent Bricks. Each sample is an independent project.
Start with the [setup guide](docs/GETTING_STARTED.md), then choose a sample.

| Sample | What you'll learn | Main files to customize |
| --- | --- | --- |
| [01 · CLI quickstart](pro-code/01-agentbricks-cli/README.md) | Run and deploy an agent with a Python tool. | `agent/agent.py`, `agent/tools/` |
| [02 · Agent memory](pro-code/02-agent-memory/README.md) | Preserve conversations, distill durable facts, and recall them in a new session. | `agent/memory.py`, `agent/transcript.py`, `resources/` |
| [03 · App scaling](pro-code/03-horizontal-scaling/README.md) | Compare one and three fixed App instances with Locust. | `agent/benchmark_model.py`, `scripts/loadtest/` |
| [04 · Genie supervisor](pro-code/04-genie-supervisor/README.md) | Delegate questions to sales and inventory Genie Agents. | `agent/supervisor.py`, `agent.toml` |
| [05 · MCP tools](pro-code/05-mcp-server/README.md) | Connect an agent to managed web-search tools. | `agent.toml`, `agent/agent.py` |
| [06 · Retail assistant](pro-code/06-retail-assistant/README.md) | Combine Genie, policy search, and optional GitHub MCP. | `agent/prompt.py`, `agent/tools/`, `data/` |
| [Lower-code · Genie Agents](lower-code/genie-agents/README.md) | Curate data context, example questions, and SQL. | `assets/`, `sql/` |

Use 01–05 to learn individual capabilities; 06 combines integrations in a larger application.

| Repository path | Purpose |
| --- | --- |
| [pro-code/](pro-code/) | Python agents, runtime adapters, and optional browser UIs. |
| [lower-code/](lower-code/README.md) | Genie configuration and synthetic data assets. |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Shared prerequisites, authentication, deployment, and cleanup. |
| [scripts/validate.sh](scripts/validate.sh) | Offline checks for every sample. |
| [docs/VALIDATION.md](docs/VALIDATION.md) | Test results and live validation evidence. |

Run `bash scripts/validate.sh` from this directory to check all samples. It may download dependencies.
