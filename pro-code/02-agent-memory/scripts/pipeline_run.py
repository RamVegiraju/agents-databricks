"""Start one memory pipeline run or wait for an existing run using the public CLI.

Usage: uv run --frozen python scripts/pipeline_run.py --profile PROFILE --pipeline ID
Resume monitoring: replace --pipeline ID with --run memory-pipelines/ID/runs/RUN_ID.
Requires the pinned Agent Bricks CLI on PATH (provided by uv run). Starting a run
uses workspace compute and model calls. A monitoring timeout leaves the run active.
"""

import argparse
import json
import subprocess
import time
from collections.abc import Callable
from typing import Any


def cli_json(profile: str, arguments: list[str]) -> dict[str, Any]:
    """Execute a public Agent Bricks command and require a JSON object response."""
    result = subprocess.run(
        ["agentbricks", "--profile", profile, "--output", "json", *arguments],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("Expected an Agent Bricks JSON object")
    return value


def wait_for_run(
    run_name: str,
    fetch: Callable[[str], dict[str, Any]],
    *,
    timeout: float,
    interval: float,
) -> int:
    """Print real run states; return 75 on timeout, 1 on failure, or 0 on success."""
    deadline = time.monotonic() + timeout
    while True:
        run = fetch(run_name)
        print(json.dumps(run, indent=2), flush=True)
        state = run.get("state")
        if state == "SUCCEEDED":
            return 0
        if state in {"FAILED", "CANCELLED"}:
            return 1
        if state != "RUNNING":
            raise ValueError(f"Unexpected pipeline state: {state!r}")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print(f"Monitoring timed out. Run remains active: {run_name}", flush=True)
            return 75
        time.sleep(min(interval, remaining))


def main() -> int:
    """Start at most one run; polling never starts another run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pipeline", help="Start one run for this pipeline")
    target.add_argument("--run", help="Monitor an existing full run resource name")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    if args.timeout <= 0 or not 0 < args.interval <= 60:
        parser.error("timeout must be positive and interval must be in (0, 60]")
    try:
        run_name = args.run
        if args.pipeline:
            started = cli_json(args.profile, ["memory", "pipeline", "run", args.pipeline])
            print(json.dumps(started, indent=2), flush=True)
            run_name = started.get("name")
        if not isinstance(run_name, str) or not run_name.startswith("memory-pipelines/"):
            raise ValueError("The pipeline API did not return a full run resource name")
        return wait_for_run(
            run_name,
            lambda name: cli_json(args.profile, ["memory", "pipeline", "runs", "get", name]),
            timeout=args.timeout,
            interval=args.interval,
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout, flush=True)
        return 1
    except (ValueError, subprocess.TimeoutExpired) as exc:
        print(str(exc), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
