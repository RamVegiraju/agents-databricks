# Agents on Databricks

Independent Agent Bricks examples:

| Sample | What it shows |
| --- | --- |
| [Agent Bricks CLI quickstart](pro-code/01-agentbricks-cli/README.md) | Run a LangGraph clock agent locally, then deploy it to Apps |
| [Agent memory](pro-code/02-agent-memory/README.md) | Save, recall, and forget facts across sessions |
| [App scale-out](pro-code/03-horizontal-scaling/README.md) | One versus three fixed App instances, compared with Locust |
| [Genie supervisor](pro-code/04-genie-supervisor/README.md) | Delegation across Genie agents |
| [MCP server](pro-code/05-mcp-server/README.md) | Add a remote MCP tool to an agent |
| [Retail assistant](pro-code/06-retail-assistant/README.md) | Advanced combined Genie, AI Search, and optional GitHub MCP example |
| [Lower-code Genie Agents](lower-code/genie-agents/README.md) | Curated Genie definitions and synthetic data |

Each sample has its own setup instructions. Python samples require Python 3.11+ and
[uv](https://docs.astral.sh/uv/). Run `bash scripts/validate.sh` for local checks; uv may download
packages from the public index. The [validation record](docs/VALIDATION.md) summarizes checks.
