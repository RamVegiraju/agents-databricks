"""Bind two existing Genie Agents without changing the rest of agent.toml."""

import argparse
import re
import tomllib
from pathlib import Path

SPACE_ID = re.compile(r"[0-9a-f]{32}\Z")
SPACE_LINE = re.compile(r'(space_id\s*=\s*")[0-9a-f]{32}("\s*})')


def bind(manifest: Path, sales: str, inventory: str) -> None:
    """Replace only the two curated Genie space IDs in a valid manifest."""
    for value in (sales, inventory):
        if not SPACE_ID.fullmatch(value):
            raise ValueError("Genie space IDs must be 32 lowercase hexadecimal characters")

    source = manifest.read_text()
    parsed = tomllib.loads(source)
    tools = {item["id"]: item for item in parsed.get("tools", [])}
    for name in ("sales", "inventory"):
        tool = tools.get(name)
        if not tool or tool.get("auth") != "app" or tool["source"].get("kind") != "genie_agent":
            raise ValueError(f"Expected an app-auth Genie Agent binding named {name}")

    sections = source.split("[[tools]]")
    replacements = {"sales": sales, "inventory": inventory}
    seen: set[str] = set()
    for index, section in enumerate(sections[1:], 1):
        match = re.search(r'^id\s*=\s*"([^"]+)"', section, re.MULTILINE)
        if match and match.group(1) in replacements:
            name = match.group(1)
            sections[index], count = SPACE_LINE.subn(
                lambda item: item.group(1) + replacements[name] + item.group(2), section
            )
            if count != 1:
                raise ValueError(f"Expected one space_id in {name} binding")
            seen.add(name)
    if seen != replacements.keys():
        raise ValueError("Could not find both Genie tool sections")

    updated = "[[tools]]".join(sections)
    tomllib.loads(updated)
    manifest.write_text(updated)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sales-space-id", required=True)
    parser.add_argument("--inventory-space-id", required=True)
    parser.add_argument("--manifest", type=Path, default=Path("agent.toml"))
    args = parser.parse_args()
    bind(args.manifest, args.sales_space_id, args.inventory_space_id)
    print("Updated sales and inventory Genie Agent bindings in", args.manifest)


if __name__ == "__main__":
    main()
