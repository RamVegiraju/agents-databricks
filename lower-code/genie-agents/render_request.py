"""Render a local Genie create-space request; never connect to Databricks."""

import argparse
import json
import re
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "assets"


def build_request(domain: str, catalog: str, schema: str, warehouse_id: str) -> dict:
    """Build an API request with reviewed source identifiers.

    Args:
        domain: Sales, inventory, or combined retail agent to render.
        catalog: Target Unity Catalog catalog name.
        schema: Target schema name.
        warehouse_id: SQL warehouse identifier.

    Returns:
        A request dictionary whose serialized_space field is a JSON string.
    """
    descriptions = {
        "sales": "Answer historical retail sales questions: revenue, units, products and regions. Does not answer inventory questions.",
        "inventory": "Answer inventory snapshot questions: stock by SKU and warehouse, and warehouse-specific reorder thresholds. Does not answer sales questions.",
        "retail": "Answer combined historical retail sales and dated inventory questions. Compare product sales with snapshot stock and flag low-stock warehouses. Does not supply replenishment policies or supplier lead times.",
    }
    if domain not in descriptions:
        raise ValueError("domain must be sales, inventory, or retail")
    for name in (catalog, schema):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("Use simple SQL identifiers for catalog and schema")
    if not warehouse_id.strip():
        raise ValueError("warehouse_id must be nonempty")
    serialized = (ASSET_DIR / f"{domain}.serialized-space.json").read_text()
    serialized = serialized.replace("northstar_demo.retail.", f"{catalog}.{schema}.")
    return {
        "title": f"Northstar {domain.title()}",
        "description": descriptions[domain],
        "warehouse_id": warehouse_id,
        "serialized_space": json.dumps(json.loads(serialized)),
    }


def main() -> None:
    """Write the rendered request to stdout for inspection or file redirection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", choices=["sales", "inventory", "retail"])
    parser.add_argument("--catalog", default="northstar_demo")
    parser.add_argument("--schema", default="retail")
    parser.add_argument("--warehouse-id", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_request(args.domain, args.catalog, args.schema, args.warehouse_id),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
