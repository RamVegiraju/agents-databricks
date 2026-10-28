# Lower-code agents

Curate a Genie Agent's data and business context without writing a custom server or agent loop.
Start with [Northstar retail Genie Agents](genie-agents/README.md).

| Path | Purpose / what to change |
| --- | --- |
| [genie-agents/assets/](genie-agents/assets/) | Table context, column descriptions, questions, and SQL examples. |
| [genie-agents/sql/](genie-agents/sql/) | Synthetic data setup and reference queries. |
| [genie-agents/render_request.py](genie-agents/render_request.py) | Render configuration for your namespace and warehouse. |
| [genie-agents/render_sql.py](genie-agents/render_sql.py) | Render SQL for the same namespace. |
| [genie-agents/tests/](genie-agents/tests/) | Local configuration and query checks. |

The [Genie supervisor](../pro-code/04-genie-supervisor/README.md) and
[retail assistant](../pro-code/06-retail-assistant/README.md) can call these curated agents.
Genie conversations have their own history; they do not automatically populate Agent Bricks memory.
