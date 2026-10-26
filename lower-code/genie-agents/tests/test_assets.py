"""Offline checks for serialized assets and fixture SQL behavior; no workspace calls."""

import importlib.util
import json
import re
import sqlite3
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_renderer(filename: str = "render_request.py") -> ModuleType:
    """Import the local renderer without installing a package."""
    spec = importlib.util.spec_from_file_location(
        filename.removesuffix(".py"), ROOT / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("domain", ["sales", "inventory"])
def test_asset_structure_and_sql_against_fixture(domain: str) -> None:
    """Check strict serialization conventions and execute examples on toy fixture rows."""
    payload = json.loads(
        (ROOT / "assets" / f"{domain}.serialized-space.json").read_text()
    )
    assert payload["version"] == 2
    table = payload["data_sources"]["tables"][0]
    assert table["identifier"] == f"northstar_demo.retail.{domain}"
    columns = table["column_configs"]
    assert [c["column_name"] for c in columns] == sorted(
        c["column_name"] for c in columns
    )
    ids = []
    for items in [
        payload["config"]["sample_questions"],
        payload["instructions"]["example_question_sqls"],
    ]:
        assert [item["id"] for item in items] == sorted(item["id"] for item in items)
        for item in items:
            assert re.fullmatch(r"[0-9a-f]{32}", item["id"])
            assert isinstance(item["question"], list)
            ids.append(item["id"])
    assert len(ids) == len(set(ids))

    # Execute the portable SELECT subset against the actual VALUES in fixtures.sql.
    # SQLite does not validate Delta DDL or Databricks-specific server behavior.
    fixture = (ROOT / "sql" / "fixtures.sql").read_text()
    fixture_match = re.search(
        rf"MERGE INTO northstar_demo.retail.{domain}.*?USING \(SELECT \* FROM VALUES(.*?)AS fixture\((.*?)\)",
        fixture,
        re.DOTALL,
    )
    assert fixture_match is not None
    values, names = fixture_match.groups()
    values = re.sub(r"DATE'([^']+)'", r"'\1'", values.strip())
    with sqlite3.connect(":memory:") as db:
        db.execute(f"CREATE TABLE {domain} ({names})")
        db.execute(f"INSERT INTO {domain} VALUES {values}")
        results = []
        for example in payload["instructions"]["example_question_sqls"]:
            sql = "\n".join(example["sql"])
            assert sql.startswith("SELECT ")
            sql = sql.replace("northstar_demo.retail.", "")
            sql = re.sub(r"DATE'([^']+)'", r"'\1'", sql)
            results.append(db.execute(sql).fetchall())
    if domain == "sales":
        assert results[0] == [
            ("SKU-100", "Trail Runner", 630.0),
            ("SKU-300", "Rain Shell", 420.0),
            ("SKU-200", "City Pack", 300.0),
        ]
        assert results[1] == [(7,)]
        assert results[2] == [("S003", "2026-10-02", "West", 4, 360.0)]
    else:
        assert [(row[0], row[2]) for row in results[0]] == [
            ("SKU-100", "Boston"),
            ("SKU-200", "Reno"),
            ("SKU-300", "Reno"),
        ]
        assert results[1] == [("SKU-100", 22)]
        assert len(results[2]) == 3


def test_render_rewrites_identifiers_inside_metadata_and_sql() -> None:
    """Ensure changing the deployment namespace updates both data source and examples."""
    request = load_renderer().build_request(
        "sales", "sandbox", "demo", "warehouse-placeholder"
    )
    assert isinstance(request["serialized_space"], str)
    payload = json.loads(request["serialized_space"])
    assert payload["data_sources"]["tables"][0]["identifier"] == "sandbox.demo.sales"
    assert "northstar_demo.retail" not in request["serialized_space"]
    assert (
        "sandbox.demo.sales"
        in payload["instructions"]["example_question_sqls"][0]["sql"][0]
    )


def test_render_rejects_unsafe_identifier() -> None:
    """Reject identifiers which cannot be safely substituted into SQL examples."""
    with pytest.raises(ValueError, match="simple SQL identifiers"):
        load_renderer().build_request(
            "sales", "catalog; DROP TABLE sales", "demo", "warehouse"
        )


def test_sql_renderer_uses_same_namespace_as_genie_assets() -> None:
    renderer = load_renderer("render_sql.py")
    for kind in ("fixtures", "validate"):
        sql = renderer.render_sql(kind, "sandbox", "demo")
        assert "northstar_demo.retail" not in sql
        assert "sandbox.demo.sales" in sql
        assert "sandbox.demo.inventory" in sql
    assert "CREATE SCHEMA IF NOT EXISTS sandbox.demo;" in renderer.render_sql(
        "fixtures", "sandbox", "demo"
    )
    with pytest.raises(ValueError, match="simple SQL identifiers"):
        renderer.render_sql("fixtures", "bad; DROP TABLE sales", "demo")


def test_combined_retail_preserves_grain_with_warehouse_fanout() -> None:
    """Execute joined examples on fixtures and an extra snapshot to catch inflated facts."""
    request = load_renderer().build_request(
        "retail", "northstar_demo", "retail", "warehouse"
    )
    payload = json.loads(request["serialized_space"])
    assert payload["version"] == 2
    assert [t["identifier"] for t in payload["data_sources"]["tables"]] == [
        "northstar_demo.retail.inventory",
        "northstar_demo.retail.sales",
    ]
    assert (
        "join_specs" not in payload["instructions"]
    )  # Raw fact-to-fact joins multiply measures.
    ids = []
    for items in [
        payload["config"]["sample_questions"],
        *payload["instructions"].values(),
    ]:
        assert [item["id"] for item in items] == sorted(item["id"] for item in items)
        ids.extend(item["id"] for item in items)
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[0-9a-f]{32}", id_) for id_ in ids)

    fixture = (ROOT / "sql" / "fixtures.sql").read_text()
    with sqlite3.connect(":memory:") as db:
        for domain in ["sales", "inventory"]:
            match = re.search(
                rf"MERGE INTO northstar_demo.retail.{domain}.*?USING \(SELECT \* FROM VALUES(.*?)AS fixture\((.*?)\)",
                fixture,
                re.DOTALL,
            )
            assert match is not None
            values, names = match.groups()
            db.execute(f"CREATE TABLE {domain} ({names})")
            values = re.sub(r"DATE'([^']+)'", r"'\1'", values.strip())
            db.execute(f"INSERT INTO {domain} VALUES {values}")
        # A different-date snapshot must not leak into stock totals or duplicate sales.
        db.execute(
            "INSERT INTO inventory SELECT '2026-10-04', product_id, product_name, category, warehouse, 999, reorder_point_units FROM inventory"
        )
        results = []
        for example in payload["instructions"]["example_question_sqls"]:
            sql = "\n".join(example["sql"]).replace("northstar_demo.retail.", "")
            sql = re.sub(r"DATE'([^']+)'", r"'\1'", sql)
            results.append(db.execute(sql).fetchall())
    assert results[0] == [
        ("SKU-100", "Trail Runner", 7, 22),
        ("SKU-200", "City Pack", 5, 25),
        ("SKU-300", "Rain Shell", 3, 14),
    ]
    assert [(r[0], r[2], r[5]) for r in results[1]] == [
        ("SKU-100", "Boston", 7),
        ("SKU-200", "Reno", 5),
        ("SKU-300", "Reno", 3),
    ]
    assert results[2] == [
        ("SKU-100", "Trail Runner", 630.0, 2),
        ("SKU-200", "City Pack", 300.0, 2),
        ("SKU-300", "Rain Shell", 420.0, 2),
    ]


def test_render_combined_retail_rewrites_both_sources() -> None:
    """Remap both data sources and every CTE in the combined retail asset."""
    request = load_renderer().build_request("retail", "sandbox", "demo", "warehouse")
    assert "northstar_demo.retail." not in request["serialized_space"]
    payload = json.loads(request["serialized_space"])
    assert [t["identifier"] for t in payload["data_sources"]["tables"]] == [
        "sandbox.demo.inventory",
        "sandbox.demo.sales",
    ]
