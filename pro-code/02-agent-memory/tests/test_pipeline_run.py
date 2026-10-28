"""Verify asynchronous monitoring never treats a pending run as successful."""

import pytest

from scripts.pipeline_run import wait_for_run


def test_waits_for_success(monkeypatch):
    replies = iter([{"state": "RUNNING"}, {"state": "SUCCEEDED"}])
    names = []
    monkeypatch.setattr("scripts.pipeline_run.time.sleep", lambda _: None)

    def fetch(name):
        names.append(name)
        return next(replies)

    assert wait_for_run("run-1", fetch, timeout=10, interval=1) == 0
    assert names == ["run-1", "run-1"]


@pytest.mark.parametrize("state", ["FAILED", "CANCELLED"])
def test_failed_run_is_not_success(state):
    assert wait_for_run("run-1", lambda _: {"state": state}, timeout=10, interval=1) == 1


def test_timeout_preserves_active_run(monkeypatch, capsys):
    times = iter([0, 11])
    monkeypatch.setattr("scripts.pipeline_run.time.monotonic", lambda: next(times))
    assert wait_for_run("run-1", lambda _: {"state": "RUNNING"}, timeout=10, interval=1) == 75
    assert "Run remains active: run-1" in capsys.readouterr().out


def test_unknown_state_fails_explicitly():
    with pytest.raises(ValueError, match="Unexpected pipeline state"):
        wait_for_run("run-1", lambda _: {}, timeout=10, interval=1)
