# Northstar retail Genie Agents

Create curated sales and inventory Genie Agents, or a combined retail agent. Genie generates SQL
and executes it on a warehouse; you supply the data definitions and examples. APIs retain the
older `space` terminology.

| Configuration | Use it for |
| --- | --- |
| `sales` | Sales questions; sales specialist in sample 04. |
| `inventory` | Stock questions; inventory specialist in sample 04. |
| `retail` | Both tables; tabular source in sample 06. |

## Before you start

For local rendering, install Python 3.11+ and uv. Workspace setup additionally needs the
[shared authentication](../../docs/GETTING_STARTED.md), an existing catalog, a dedicated demo
schema, and a SQL warehouse. Creating fixtures requires schema/table write privileges; querying
requires the relevant warehouse, Genie, and data access.

```bash
cd lower-code/genie-agents
export PROFILE="my-workspace"
export CATALOG="YOUR_CATALOG"
export SCHEMA="YOUR_SCHEMA"
export WAREHOUSE_ID="YOUR_WAREHOUSE_ID"
uv sync --frozen --group dev
uv run --frozen pytest -q
```

## Set up data and agents

Render files locally; these commands do not create remote resources:

```bash
uv run --frozen python render_sql.py fixtures --catalog "$CATALOG" --schema "$SCHEMA" > /tmp/northstar-fixtures.sql
uv run --frozen python render_sql.py validate --catalog "$CATALOG" --schema "$SCHEMA" > /tmp/northstar-validate.sql
uv run --frozen python render_request.py sales --catalog "$CATALOG" --schema "$SCHEMA" \
  --warehouse-id "$WAREHOUSE_ID" > /tmp/northstar-sales-create.json
uv run --frozen python render_request.py inventory --catalog "$CATALOG" --schema "$SCHEMA" \
  --warehouse-id "$WAREHOUSE_ID" > /tmp/northstar-inventory-create.json
```

Review the generated files. Run the fixture SQL, then validation SQL, in your workspace's SQL editor.
Use a dedicated schema: fixture MERGEs do not remove unrelated data. In the demo, revenue is net USD
after discounts, and low stock means `on_hand_units < reorder_point_units`. Inventory is a dated
snapshot; never sum across snapshot dates.

Create the two agents once:

```bash
databricks genie create-space --json @/tmp/northstar-sales-create.json --profile "$PROFILE" --output json
databricks genie create-space --json @/tmp/northstar-inventory-create.json --profile "$PROFILE" --output json
```

Save the returned `space_id` values for sample 04. For sample 06, instead render `retail` with the
same arguments and create that combined configuration. Repeating create commands creates new agents;
update an existing agent when changing its curation.

Alternatively, use the Genie UI to create agents with the same tables, descriptions, sample
questions, and SQL examples from `assets/`.

## Try it

Open each agent in the Genie UI, or call the API:

```bash
databricks genie start-conversation 'YOUR_SALES_SPACE_ID' \
  'What was net revenue by product from October 1 through October 3, 2026?' \
  --no-wait --profile "$PROFILE" --output json
databricks genie get-message 'YOUR_SALES_SPACE_ID' 'CONVERSATION_ID' 'MESSAGE_ID' \
  --profile "$PROFILE" --output json
```

Poll until `COMPLETED`, `FAILED`, or `CANCELLED`. Inspect SQL and query attachments; fetch rows with
`databricks genie get-message-attachment-query-result SPACE_ID CONVERSATION_ID MESSAGE_ID ATTACHMENT_ID`.
For inventory, ask “Which SKU/warehouse pairs were below reorder point on October 3, 2026?”
Reuse the Genie conversation ID for follow-ups. Queries can start warehouse compute.

## Customize

| File | Purpose / what to change |
| --- | --- |
| [assets/](assets/) | Table/column context, questions, metric definitions, and reviewed SQL examples. |
| [sql/fixtures.sql](sql/fixtures.sql) | Synthetic tables and fixture MERGEs. |
| [sql/validate.sql](sql/validate.sql) | Reference queries and expected fixture results. |
| [render_request.py](render_request.py) | Namespace remapping and create-request encoding. |
| [render_sql.py](render_sql.py) | Fixture/validation SQL namespace remapping. |
| [tests/](tests/), [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) | Local checks, dependencies, and generated lockfile. |

Edit checked-in assets, not generated request JSON. The renderer encodes `serialized_space` as a
JSON string. For combined queries, aggregate sales and one inventory snapshot to compatible grains
before joining. Validate your definitions and SQL on the target warehouse; local tests do not verify
service acceptance or permissions.

See [Genie setup](https://docs.databricks.com/aws/en/genie-agents/set-up) and the
[Conversation API](https://docs.databricks.com/aws/en/genie-agents/conversation-api).
