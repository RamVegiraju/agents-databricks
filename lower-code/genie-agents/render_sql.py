"""Render the reviewed fixture or validation SQL for a chosen UC namespace."""

import argparse
import re
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"


def render_sql(kind: str, catalog: str, schema: str) -> str:
    """Replace only the demo table prefix after validating simple UC names."""
    if kind not in {"fixtures", "validate"}:
        raise ValueError("kind must be fixtures or validate")
    for name in (catalog, schema):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("Use simple SQL identifiers for catalog and schema")
    sql = (SQL_DIR / f"{kind}.sql").read_text(encoding="utf-8")
    return sql.replace("northstar_demo.retail.", f"{catalog}.{schema}.").replace(
        "northstar_demo.retail;", f"{catalog}.{schema};"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["fixtures", "validate"])
    parser.add_argument("--catalog", default="northstar_demo")
    parser.add_argument("--schema", default="retail")
    args = parser.parse_args()
    print(render_sql(args.kind, args.catalog, args.schema), end="")


if __name__ == "__main__":
    main()
