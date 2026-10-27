import json
import sys

import pytest

from scripts import grant_app_access
from scripts.grant_app_access import planned_resources


def test_grants_preserve_genie_and_tracing_resources_and_are_idempotent():
    existing = [
        {"name": "genie", "genie_space": {"space_id": "example"}},
        {"name": "trace", "experiment": {"experiment_id": "example"}},
    ]
    app = {"resources": existing}

    resources = planned_resources(app, "demo.retail")

    assert resources[:2] == existing
    assert len(resources) == 5
    assert {
        resource["uc_securable"]["securable_full_name"]
        for resource in resources[2:]
    } == {"demo.retail.sales", "demo.retail.inventory", "demo.retail.policy_index"}
    assert all(resource["uc_securable"]["permission"] == "SELECT" for resource in resources[2:])
    assert planned_resources({"resources": resources}, "demo.retail") == resources
    assert app["resources"] == existing


def test_grants_reject_ambiguous_resource_names():
    app = {"resources": [{"name": "retail-sales", "uc_securable": {"securable_full_name": "other.sales"}}]}

    with pytest.raises(ValueError, match="already belongs"):
        planned_resources(app, "demo.retail")


def test_grants_reject_existing_binding_without_select():
    app = {"resources": [{"name": "sales", "uc_securable": {"securable_full_name": "demo.retail.sales", "permission": "USE"}}]}

    with pytest.raises(ValueError, match="needs SELECT"):
        planned_resources(app, "demo.retail")


def test_grants_reject_invalid_schema():
    with pytest.raises(ValueError, match="schema must be"):
        planned_resources({}, "demo.retail;DROP")


def test_grants_support_hyphenated_catalog_and_require_select():
    resources = planned_resources({}, "demo-catalog.retail-schema")
    assert resources[0]["uc_securable"]["securable_full_name"] == "demo-catalog.retail-schema.sales"

    resources[0]["uc_securable"]["permission"] = "MODIFY"
    with pytest.raises(ValueError, match="needs SELECT"):
        planned_resources({"resources": resources}, "demo-catalog.retail-schema")


def test_apply_updates_only_resources_and_keeps_existing_bindings(monkeypatch):
    calls = []

    def fake_cli_json(*args):
        calls.append(args)
        if args[:2] == ("apps", "get"):
            return {"resources": [{"name": "genie", "genie_space": {"space_id": "example"}}]}
        return {"status": {"state": "SUCCEEDED"}}

    monkeypatch.setattr(grant_app_access, "cli_json", fake_cli_json)
    monkeypatch.setattr(sys, "argv", ["grant_app_access", "--profile", "chosen", "--app", "demo-app", "--schema", "demo.retail", "--apply"])

    grant_app_access.main()

    assert calls[0] == ("apps", "get", "demo-app", "--profile", "chosen", "-o", "json")
    assert calls[1][:3] == ("apps", "create-update", "demo-app")
    assert calls[1][5:] == ("--profile", "chosen", "-o", "json")
    update = json.loads(calls[1][4])
    assert update["update_mask"] == "resources"
    assert update["app"]["resources"][0]["genie_space"]["space_id"] == "example"
    assert len(update["app"]["resources"]) == 4
