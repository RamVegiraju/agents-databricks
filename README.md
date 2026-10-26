# Agents on Databricks

Examples of pro-code agents built with Agent Bricks and lower-code curated Genie Agents.
Start with Hello World, then explore orchestration and data integrations.

| Example | Features |
| --- | --- |
| [Hello World + memory](pro-code/01-hello-memory/README.md) | LangGraph, local tool, conversation state, memory tools, automatic recall and memory pipelines |
| [Horizontal scaling walkthrough](pro-code/01-hello-memory/HORIZONTAL_SCALING.md) | One-to-three App instance update, replica probe, and Locust concurrency comparison |
| [Genie supervisor](pro-code/02-genie-supervisor/README.md) | LangGraph supervisor over sales and inventory Genie subagents |
| [Retail assistant](pro-code/03-retail-assistant/README.md) | Browser chat, Genie analytics, AI Search document ingestion/retrieval, external MCP through a UC HTTP connection |
| [Lower-code Genie Agents](lower-code/genie-agents/README.md) | UI walkthrough, synthetic retail data and reusable Genie definitions |

Each example runs independently and includes setup instructions, configuration and tests.
Retail data and policies are synthetic.

## Getting started

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cd pro-code/01-hello-memory
uv sync --frozen --group dev
uv run --frozen pytest -q
uv run --frozen agentbricks doctor .
```

Follow the example's README to select a Databricks profile and run against workspace services.
Setup and deployment are explicit steps; startup and tests do not provision external resources.

## Validation

Built against Agent Bricks **0.6.0**, Databricks SDK **0.154.0** and databricks-langchain **0.21.0**.
**145 offline tests pass; 3 live tests are skipped.** All three pro-code examples pass `doctor`.

No examples have been deployed or tested end to end against live Databricks services. Offline tests
use injected model/storage responses; `doctor` inspects project structure without executing the app.
See [validation details and remaining checks](docs/VALIDATION.md).

After installing each example's dependencies, rerun the offline suite with `bash scripts/validate.sh`.

## Databricks documentation

- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli)
- [Agent Server and durable execution](https://docs.databricks.com/aws/en/agents/deploy/agent-server)
- [Sessions, memory and pipelines](https://docs.databricks.com/aws/en/agents/custom-agents/stateful-agents)
- [Genie Agents API](https://docs.databricks.com/aws/en/genie-agents/conversation-api)
- [External MCP registration](https://docs.databricks.com/aws/en/ai-gateway/mcp-service-reference)
