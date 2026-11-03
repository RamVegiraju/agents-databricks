"""Pure inventory lookup; tools read synthetic data and never reserve or ship stock."""

import json
from pathlib import Path
from typing import Any

INVENTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "inventory.json"


def lookup_inventory(sku: str, destination: str) -> dict[str, Any]:
    """Read available units and transit estimates from the bundled sample inventory.

    Args:
        sku: Sample product identifier, such as MX-100.
        destination: Supported destination city: Boston or Austin.

    Returns:
        Synthetic stock facts with reservations subtracted, or a structured lookup error.
        Transit estimates use business days and are not delivery guarantees.

    Raises:
        OSError: If the packaged inventory cannot be read.
        ValueError: If the packaged JSON is invalid.

    Side effects:
        Reads one local file. Does not make network calls or modify inventory.
    """
    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    product = inventory["products"].get(sku.upper())
    if product is None:
        return {"error": "unknown_sku", "sku": sku, "available_skus": list(inventory["products"])}
    city = destination.strip().title()
    if city not in {"Boston", "Austin"}:
        return {"error": "unsupported_destination", "supported_destinations": ["Boston", "Austin"]}
    warehouses = [
        {
            "warehouse": warehouse["name"],
            "available_units": max(warehouse["on_hand"] - warehouse["reserved"], 0),
            "transit_business_days": warehouse["transit_business_days"][city],
        }
        for warehouse in product["warehouses"]
    ]
    return {
        "data_kind": inventory["data_kind"],
        "snapshot_date": inventory["snapshot_date"],
        "sku": sku.upper(),
        "product_name": product["name"],
        "destination": city,
        "warehouses": sorted(warehouses, key=lambda item: item["transit_business_days"]),
        "total_available_units": sum(item["available_units"] for item in warehouses),
    }
