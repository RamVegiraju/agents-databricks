# Northstar retail: two curated Genie Agents

This is the lower-code counterpart to the pro-code LangGraph examples. A retail analyst uses one Genie Agent for sales and another for inventory, or a combined retail agent for the full-stack example. Each configuration includes column descriptions, entity matching for categorical dimensions, three sample questions, and three representative SQL examples. These are portable assets; rendering and local tests create no workspace resources.

| Agent | Data | Example |
|---|---|---|
| Northstar Sales | `northstar_demo.retail.sales` | Which products generated the most net revenue October 1–3, 2026? |
| Northstar Inventory | `northstar_demo.retail.inventory` | Which SKU/warehouse pairs were below reorder point on October 3, 2026? |
| Northstar Retail (sample 06) | Both tables | Compare October 1–3 sales with October 3 stock by SKU. |

The first two are separate domain agents for the supervisor. The combined retail configuration is an alternative for the full-stack sample's single tabular agent; it does not replace those separate agents.

Genie Agents were previously called Genie Spaces. The SDK, CLI, IDs, and REST paths retain `space` terminology. Genie handles SQL generation and execution; it does not require your own Agent Bricks server. [Genie API documentation](https://docs.databricks.com/aws/en/genie-agents/conversation-api)

## Demo semantics and assets

This fictional example defines net revenue as the supplied USD amount after discounts, excludes returns and tax, and defines low stock as `on_hand_units < reorder_point_units` for each warehouse. Inventory is a point-in-time snapshot: never sum across dates. These are demo definitions, not inferred definitions for a real business.

- [fixtures.sql](sql/fixtures.sql): opt-in Delta DDL and idempotent fixture merges; creates a schema and two tables. The catalog must already exist. Review object names before running.
- [validate.sql](sql/validate.sql): read-only reference checks with expected fixture results.
- [sales configuration](assets/sales.serialized-space.json) and [inventory configuration](assets/inventory.serialized-space.json): unescaped version 2 serialized-space objects.
- [combined retail configuration](assets/retail.serialized-space.json): two tables and three CTE examples that aggregate sales and stock at compatible grains before joining. No raw fact-to-fact join is registered: joining sale lines directly to warehouse snapshots multiplies totals. Each example explicitly scopes the sales period and one inventory snapshot date.
- [render_request.py](render_request.py): local-only renderer that wraps the selected configuration in a create request, optionally remapping catalog/schema. It makes no network calls.
- [render_sql.py](render_sql.py): local-only renderer for fixture and validation SQL in the same catalog/schema.

Use a dedicated empty demo schema: `IF NOT EXISTS` does not verify an existing table's schema, and fixture merges do not remove unrelated rows. The catalog must already exist. Pass the same catalog and schema to both renderers and to the other samples' setup commands.

For a real rollout, confirm business definitions, inspect data, and consider governed metric views before curating Genie. These compact raw-table fixtures also demonstrate sale-line and warehouse-level detail. No trusted/certified SQL label or benchmark claims are made. SQL examples were checked locally on synthetic rows, not on a Databricks warehouse. Add warehouse-tested benchmarks and additional examples before production use. [Curation guidance](https://docs.databricks.com/aws/en/genie-agents/conversation-api#create-or-select-a-genie-agent)

## UI path

After separately reviewing and setting up the fixture tables, open **Genie Agents → New**, add only the sales table, and create the agent. Review any automatically suggested context from Genie Code. Configure an existing pro or serverless SQL warehouse, and set the title and domain description from the rendered request. Add sample questions and SQL examples from the sales asset. Configure column descriptions and categorical matching from `column_configs`. Repeat with inventory. The JSON is the code-managed equivalent of this curation; it is not an upload to the chat interface. Test each agent with the fixed-date questions before sharing it. [Create and manage a Genie Agent](https://docs.databricks.com/aws/en/genie-agents/set-up)

## Local inspection and tests

From this directory:

```bash
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen python render_sql.py fixtures --catalog '<catalog>' --schema '<schema>' > /tmp/northstar-fixtures.sql
uv run --frozen python render_sql.py validate --catalog '<catalog>' --schema '<schema>' > /tmp/northstar-validate.sql
uv run --frozen python render_request.py sales --catalog '<catalog>' --schema '<schema>' --warehouse-id '<warehouse-id>' > /tmp/northstar-sales-create.json
uv run --frozen python render_request.py inventory --catalog '<catalog>' --schema '<schema>' --warehouse-id '<warehouse-id>' > /tmp/northstar-inventory-create.json
# Alternative tabular agent for sample 06:
uv run --frozen python render_request.py retail --catalog '<catalog>' --schema '<schema>' --warehouse-id '<warehouse-id>' > /tmp/northstar-retail-create.json
```

The rendering commands only write local SQL and JSON files. The `serialized_space` request property is a JSON **string**, while the checked-in asset is a JSON **object**; the renderer handles encoding. The tests verify serialization rules, namespace remapping, and run all nine example SELECTs against the actual fixture VALUES in SQLite. Combined queries are also checked with an extra inventory snapshot to catch date leakage and inflated sales. SQLite validates this portable query subset, not Delta DDL or Genie service acceptance.

Version 2, lowercase 32-hex IDs, string arrays, sorting, and column settings were checked against the current [serialized-space rules](https://docs.databricks.com/aws/en/genie-agents/conversation-api#validation-rules-for-serialized_space) on October 26, 2026. Some older examples earlier on that same page still use version 1; the explicit validation section says to use 2 for new agents. SDK 0.157.0 takes `serialized_space: str` and does not validate its internals. Validate service acceptance in each target workspace.

## CLI lifecycle

All commands below contact a workspace. Replace placeholders and review the rendered payload first. CLI syntax was inspected locally with Databricks CLI 1.20.0 `--help`.

**Provisioning:** execute the reviewed `/tmp/northstar-fixtures.sql` in the SQL editor using the chosen warehouse. Run `/tmp/northstar-validate.sql` to inspect the fixture results. Then these commands create persistent Genie Agent objects; running them again creates additional agents.

```bash
databricks genie create-space --json @/tmp/northstar-sales-create.json --profile '<profile>' --output json
databricks genie create-space --json @/tmp/northstar-inventory-create.json --profile '<profile>' --output json
```

When `--json` provides the full body, the required positional fields come from that body. The underlying command signature is `databricks genie create-space WAREHOUSE_ID SERIALIZED_SPACE`. Record the returned `space_id` values as `SALES_GENIE_SPACE_ID` and `INVENTORY_GENIE_SPACE_ID` for use by the pro-code supervisor.

For the full-stack sample, use the alternative reviewed retail payload with `databricks genie create-space --json @/tmp/northstar-retail-create.json --profile '<profile>' --output json` and configure its returned space ID in that sample. This provisions a third agent only when explicitly run.

The combined asset's text instructions require missing dates to be clarified, both periods to be stated in summaries, and observed low stock to be distinguished from purchase recommendations. Structured descriptions and SQL examples own the grain and date filters; the text is limited to global conversation/summary behavior. Review these instructions with fixed-date prompts and omitted-date prompts. They do not authorize the tabular agent to invent policy or lead times; the full-stack example supplies that evidence from its separate policy retrieval source.

**Metadata read:** this exports configuration and does not ask Genie to execute a query.

```bash
databricks genie get-space '<sales-space-id>' --include-serialized-space --profile '<profile>' --output json
```

**Query:** these create conversation/message objects, invoke Genie, and can execute SQL on the configured warehouse; they are not read-only metadata calls.

```bash
databricks genie start-conversation '<sales-space-id>' 'What was net revenue by product from October 1 through October 3, 2026?' --no-wait --profile '<profile>' --output json
databricks genie get-message '<sales-space-id>' '<conversation-id>' '<message-id>' --profile '<profile>' --output json
databricks genie create-message '<sales-space-id>' '<conversation-id>' 'Break that down by region for the same period.' --no-wait --profile '<profile>' --output json
```

Poll until a terminal status (`COMPLETED`, `FAILED`, or `CANCELLED`). Inspect generated SQL, text, errors, and query attachment IDs. Fetch result rows with `databricks genie get-message-attachment-query-result SPACE_ID CONVERSATION_ID MESSAGE_ID ATTACHMENT_ID`. A follow-up must reuse its Genie conversation ID; an unrelated question starts a new conversation. [Conversation API](https://docs.databricks.com/aws/en/genie-agents/conversation-api)

## SDK equivalent

This is an alternative to CLI creation, not a second setup step. Run from this directory after configuring authentication and reviewing the request. The create call provisions an agent; the query call starts a conversation and may execute warehouse SQL.

```python
import json
from pathlib import Path
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="<profile>")
request = json.loads(Path("/tmp/northstar-sales-create.json").read_text())
space = w.genie.create_space(**request)  # Creates a persistent Genie Agent.
message = w.genie.start_conversation_and_wait(
    space_id=space.space_id,
    content="What was net revenue by product from October 1 through October 3, 2026?",
)
print(json.dumps(message.as_dict(), indent=2))
```

Use `w.genie.get_space(space_id, include_serialized_space=True)` to export and `w.genie.update_space(space_id, serialized_space=...)` to change an existing agent rather than creating duplicates. Code-managed curation controls the same resource as the UI. The SDK signatures above were inspected in SDK 0.157.0.

## Permissions, costs, and integration boundaries

For API setup, the API documentation lists SQL entitlement and `CAN USE` on a suitable warehouse. Data access requires `USE CATALOG`, `USE SCHEMA`, and `SELECT` on the sources; callers also need access to the Genie Agent. Fixture setup additionally needs schema/table creation and data-write privileges. App service principals need their own effective permissions; access by the developer does not confer access on the app. [API prerequisites and authentication](https://docs.databricks.com/aws/en/genie-agents/conversation-api#prerequisites)

The UI sharing documentation distinguishes consumers: warehouse credentials are embedded by the author, so end users do not need direct warehouse access, while Unity Catalog data access is evaluated per user. Review that distinction for your authentication model. [Sharing and permissions](https://docs.databricks.com/aws/en/genie-agents/set-up)

Fixture execution and Genie SQL queries can start a warehouse and incur compute charges. Genie service-principal usage is also billed; check current terms before running an application. [Genie billing overview](https://docs.databricks.com/aws/en/genie/). No warehouse, table, Genie Agent, or application is created by local rendering/tests. The sample does not grant privileges, enable previews, deploy apps, or automate cleanup.

The LangGraph supervisor can wrap each reviewed Genie Agent as a tool. It owns routing and synthesis; each Genie Agent owns SQL in its domain. Genie conversations have their own history. They do not automatically become Agent Bricks Session Store records or durable memories: persist relevant inputs/results in the outer application's session if you want an Agent Bricks memory pipeline to process them. The outer application must map trusted user identity to `actor_id` and manage Genie conversation IDs separately.
