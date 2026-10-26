# Agents on Databricks

Independent Agent Bricks examples:

| Sample | What it shows |
| --- | --- |
| [Agent Bricks CLI quickstart](pro-code/01-agentbricks-cli/README.md) | Run a LangGraph clock agent locally, then deploy it to Apps |
| [Genie supervisor](pro-code/02-genie-supervisor/README.md) | Delegation across Genie agents |
| [Retail assistant](pro-code/03-retail-assistant/README.md) | Chat, Genie, AI Search, and external MCP |
| [App scale-out](pro-code/04-horizontal-scaling/README.md) | Two Apps with one versus three fixed instances, compared with Locust |
| [Lower-code Genie Agents](lower-code/genie-agents/README.md) | Curated Genie definitions and synthetic data |

In the scaling sample's latest two-App 16-user run, three instances completed **5.69 req/s** versus
**2.25 req/s** on one instance (**2.53×**). The [results](pro-code/04-horizontal-scaling/BENCHMARK_RESULTS.md)
explain the workload, MLflow trace cross-check, and limits of this single run.

Each sample has its own setup instructions. Python samples require Python 3.11+ and
[uv](https://docs.astral.sh/uv/). Run `bash scripts/validate.sh` for local checks; uv may download
packages from the public index. The [validation record](docs/VALIDATION.md) covers the original
offline examples; the scaling sample has its own measured results.
