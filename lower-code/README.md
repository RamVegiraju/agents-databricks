# Lower-code agents

[Northstar retail Genie Agents](genie-agents/README.md) demonstrates separate curated agents for sales and inventory, plus a combined retail configuration for the full-stack sample. Genie owns SQL generation, warehouse execution, and conversation handling; you curate data and business context. No custom server or agent loop is required.

The pro-code supervisor examples can call these same agents by space ID. Genie conversation history is separate from an Agent Bricks Session Store and is not automatically ingested into an Agent Bricks memory pipeline.

## Repository structure and adaptation

| Path | Purpose | What to customize |
| --- | --- | --- |
| [genie-agents/assets/](genie-agents/assets/) | Sales, inventory, and combined retail curation. | Your domain context, columns, questions, and reviewed SQL examples. |
| [genie-agents/sql/](genie-agents/sql/) | Explicit synthetic setup and reference validation SQL. | Your data model and metric checks; fixture setup is optional for existing data. |
| [genie-agents/render_request.py](genie-agents/render_request.py) | Offline create-request rendering. | Your namespace/warehouse arguments and any new domain descriptions. |
| [genie-agents/render_sql.py](genie-agents/render_sql.py) | Offline SQL namespace rendering. | Use the same target catalog/schema as the request renderer. |
| [genie-agents/tests/](genie-agents/tests/) | Local serialization and SQL fixture checks. | Cases that capture your business definitions and joins. |
| [genie-agents/README.md](genie-agents/README.md) | Full setup, file map, API/UI workflow, and permissions. | Follow this before creating or updating Genie resources. |

Start with data semantics and curation, then render/review payloads and validate in your workspace.
Generated request JSON and rendered SQL are outputs; edit the checked-in assets as the source.
Custom routing belongs in the pro-code supervisor, not in these local renderers.
