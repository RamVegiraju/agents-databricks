"""Pure data/tool checks. These tests make no inference calls and do not replace agent tests."""

from agent.tools import lookup_inventory


def test_available_stock_excludes_reservations_and_sorts_by_transit():
    facts = lookup_inventory("MX-100", "Boston")
    assert [
        (row["available_units"], row["transit_business_days"]) for row in facts["warehouses"]
    ] == [(8, 1), (15, 2), (22, 4)]
    assert facts["total_available_units"] == 45


def test_shortage_case_has_only_five_available_units():
    assert lookup_inventory("RX-300", "Boston")["total_available_units"] == 5


def test_unknown_sku_and_destination_do_not_invent_stock():
    assert lookup_inventory("UNKNOWN", "Boston")["error"] == "unknown_sku"
    assert lookup_inventory("MX-100", "London")["error"] == "unsupported_destination"
