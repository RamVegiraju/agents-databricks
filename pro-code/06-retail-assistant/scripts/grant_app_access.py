"""Attach the retail tables and policy index to a deployed App.

Preview by default. Applying preserves every existing App resource, including
Agent Bricks' Genie and tracing resources.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from typing import Any


def planned_resources(app: dict[str, Any], schema: str) -> list[dict[str, Any]]:
    """Add missing SELECT resources without replacing unrelated App resources."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*", schema):
        raise ValueError("schema must be catalog.schema using lowercase names")
    resources = list(app.get("resources") or [])
    for suffix in ("sales", "inventory", "policy_index"):
        full_name = f"{schema}.{suffix}"
        existing = next(
            (
                resource["uc_securable"]
                for resource in resources
                if resource.get("uc_securable", {}).get("securable_full_name") == full_name
            ),
            None,
        )
        if existing:
            if existing.get("permission") != "SELECT":
                raise ValueError(f"Existing App resource for {full_name} needs SELECT")
            continue
        name = f"retail-{suffix.replace('_', '-')}"
        if any(resource.get("name") == name for resource in resources):
            raise ValueError(f"App resource name {name!r} already belongs to another resource")
        resources.append(
            {
                "name": name,
                "uc_securable": {
                    "securable_type": "TABLE",
                    "securable_full_name": full_name,
                    "permission": "SELECT",
                },
            }
        )
    return resources


def cli_json(*args: str) -> dict[str, Any]:
    """Run a Databricks CLI JSON command, surfacing its error on failure."""
    return json.loads(subprocess.check_output(("databricks", *args), text=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    app = cli_json("apps", "get", args.app, "--profile", args.profile, "-o", "json")
    resources = planned_resources(app, args.schema)
    added = len(resources) - len(app.get("resources") or [])
    if not args.apply:
        print(json.dumps({"mode": "preview", "app": args.app, "added": added, "resources": resources}, indent=2))
        return
    if not added:
        print("All three retail data resources are already attached.")
        return
    result = cli_json(
        "apps", "create-update", args.app,
        "--json", json.dumps({"update_mask": "resources", "app": {"resources": resources}}),
        "--profile", args.profile, "-o", "json",
    )
    state = result.get("status", {}).get("state")
    if state != "SUCCEEDED":
        raise RuntimeError(f"App resource update did not succeed: {state}")
    print(f"Attached {added} retail data resource(s) to {args.app}.")


if __name__ == "__main__":
    main()
