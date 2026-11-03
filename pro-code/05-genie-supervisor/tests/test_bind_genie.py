"""The binding helper must keep the manifest parseable with both Genie tools."""

import tomllib
from pathlib import Path

import pytest

from bind_genie import bind


def test_bind_existing_genie_tools(tmp_path: Path) -> None:
    source = Path("agent.toml").read_text()
    manifest = tmp_path / "agent.toml"
    manifest.write_text(source)

    bind(manifest, "a" * 32, "b" * 32)

    parsed = tomllib.loads(manifest.read_text())
    assert [(item["id"], item["source"]["space_id"]) for item in parsed["tools"]] == [
        ("sales", "a" * 32),
        ("inventory", "b" * 32),
    ]
    assert parsed["session_store"]["name"] == "retail-supervisor-sessions"


def test_bad_id_does_not_change_manifest(tmp_path: Path) -> None:
    source = Path("agent.toml").read_text()
    manifest = tmp_path / "agent.toml"
    manifest.write_text(source)

    with pytest.raises(ValueError, match="32 lowercase"):
        bind(manifest, "invalid", "b" * 32)

    assert manifest.read_text() == source
