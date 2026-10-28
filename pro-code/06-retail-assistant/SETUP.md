# Set up the retail assistant

Run from `pro-code/06-retail-assistant` after installing dependencies. Choose a profile, existing
catalog, dedicated schema, warehouse, and search endpoint. Use the same namespace throughout.
The examples use `YOUR_CATALOG.YOUR_SCHEMA`; replace it before applying changes.

## 1. Bind the retail Genie Agent

Follow the [lower-code setup](../../lower-code/genie-agents/README.md) to create the synthetic tables
and the **combined `retail` configuration** containing both sales and inventory. Sample 04's
sales-only agent cannot answer mixed stock questions.

```bash
uv run --frozen agentbricks --profile "$PROFILE" tools add genie-agent \
  YOUR_RETAIL_SPACE_ID --name retail --auth app
```

The tool adapter supplies ask/poll/query-result tools. The runtime principal needs access to the
Genie Agent, warehouse, and data under its configured security model.

## 2. Ingest policies and create the search index

Preview the chunks, then ingest into a CDF-enabled Delta table:

```bash
uv run --frozen python -m scripts.ingest_policies --table YOUR_CATALOG.YOUR_SCHEMA.policy_chunks
uv run --frozen python -m scripts.ingest_policies \
  --table YOUR_CATALOG.YOUR_SCHEMA.policy_chunks \
  --profile "$PROFILE" --warehouse-id YOUR_WAREHOUSE_ID --apply
```

Unchanged chunks are idempotent. Removed or shortened documents need stale-chunk reconciliation
or a versioned source table; the script does not delete stale chunks.

Create an endpoint only if a suitable one does not exist:

```bash
uv run --frozen python -m scripts.create_search_index --action endpoint \
  --endpoint YOUR_ENDPOINT --profile "$PROFILE" --apply
databricks vector-search-endpoints get-endpoint YOUR_ENDPOINT --profile "$PROFILE"
```

Wait for ONLINE, then create the index:

```bash
uv run --frozen python -m scripts.create_search_index --action index \
  --endpoint YOUR_ENDPOINT --index YOUR_CATALOG.YOUR_SCHEMA.policy_index \
  --table YOUR_CATALOG.YOUR_SCHEMA.policy_chunks --profile "$PROFILE" --apply
databricks vector-search-indexes get-index YOUR_CATALOG.YOUR_SCHEMA.policy_index --profile "$PROFILE"
```

This is a triggered Delta Sync index with `databricks-gte-large-en` embeddings. Wait for readiness.
After later source changes, sync and inspect readiness again:

```bash
uv run --frozen python -m scripts.create_search_index --action sync \
  --index YOUR_CATALOG.YOUR_SCHEMA.policy_index --profile "$PROFILE" --apply
```

Setup needs source-table/CDF privileges, search creation permissions, and embedding-model access.
Runtime needs parent catalog/schema use and index read access. Configure `POLICY_INDEX_NAME` and
the App grants as shown in the [README](README.md#run); deployment cannot infer this Python tool's dependencies.

## 3. Optional GitHub MCP

The GitHub hosted read-only MCP service requires a credential authorized for the target repositories.
Supply `MCP_SERVER_TOKEN` securely through the environment; never put it in source or command history.
The script registers a UC HTTP connection and MCP service with only file-read and code-search tools.

```bash
uv run --frozen python -m scripts.register_mcp --schema YOUR_CATALOG.YOUR_SCHEMA
# After reviewing the preview and supplying MCP_SERVER_TOKEN:
uv run --frozen python -m scripts.register_mcp \
  --schema YOUR_CATALOG.YOUR_SCHEMA --profile "$PROFILE" --apply
uv run --frozen agentbricks --profile "$PROFILE" tools add mcp \
  YOUR_CATALOG.YOUR_SCHEMA.github_docs --name github_docs --auth app
```

Registration needs parent use privileges, schema connection/service creation privileges, and
connection access. Runtime needs service execution access. If registration partially succeeds,
inspect and reuse the created connection; the script does not roll back or overwrite resources.
See [GitHub remote MCP](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md).

Return to [Run](README.md#run) to start the local or deployed assistant. Resource creation and
queries can incur warehouse, search, embedding/model, and storage charges independently of App compute.
