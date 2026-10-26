"""Run the same Locust concurrency sweep against one deployed App configuration."""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


def token_for(profile: str) -> str:
    if supplied := os.getenv("APP_BEARER_TOKEN"):
        return supplied
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    token = json.loads(result.stdout).get("access_token")
    if not token:
        raise RuntimeError("No U2M token returned; use APP_BEARER_TOKEN for M2M auth")
    return token


def request_json(
    url: str, token: str, routing_key: str, body: dict | None, timeout: int
) -> dict:
    request = Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Routing-Key": routing_key,
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def preflight(url: str, token: str, prompt: str, timeout: int) -> None:
    session_id = str(uuid4())
    body = {
        "id": str(uuid4()),
        "session_id": session_id,
        "input": {"messages": [{"role": "user", "content": prompt}]},
        "background": False,
        "stream": False,
    }
    result = request_json(f"{url}/api/invocations", token, session_id, body, timeout)
    output = result.get("output") if isinstance(result, dict) else None
    if (
        not isinstance(result, dict)
        or result.get("id") != body["id"]
        or result.get("status") != "completed"
        or not isinstance(output, dict)
        or output.get("status") != "completed"
    ):
        raise RuntimeError("Preflight invocation did not complete")


def probe_replicas(url: str, token: str, keys: int, timeout: int) -> dict[str, int]:
    replicas: Counter[str] = Counter()
    for _ in range(keys):
        result = request_json(f"{url}/api/replica", token, str(uuid4()), None, timeout)
        replica_id = result.get("replica_id")
        if not isinstance(replica_id, str) or not replica_id:
            raise RuntimeError("/api/replica did not return a replica_id")
        replicas[replica_id] += 1
    return dict(replicas)


def read_stats(path: Path) -> dict:
    return json.loads(path.read_text())


def run(args: argparse.Namespace) -> dict:
    url = args.app_url.rstrip("/")
    token = token_for(args.profile)
    replicas = probe_replicas(url, token, args.probe_keys, args.timeout)
    preflight(url, token, args.prompt, args.timeout)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        APP_BEARER_TOKEN=token,
        LOADTEST_PROMPT=args.prompt,
        LOADTEST_TIMEOUT=str(args.timeout),
    )
    levels = []
    for users in args.users:
        stage = args.output_dir / f"users-{users}"
        stage.mkdir(exist_ok=True)
        environment["LOADTEST_SUMMARY_FILE"] = str(stage / "final-summary.json")
        command = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(Path(__file__).with_name("locustfile.py")),
            "--host",
            url,
            "--headless",
            "--users",
            str(users),
            "--spawn-rate",
            str(max(users, 10)),
            "--run-time",
            f"{args.duration_seconds}s",
            "--stop-timeout",
            str(args.timeout),
            "--csv",
            str(stage / "locust"),
            "--csv-full-history",
            "--html",
            str(stage / "locust.html"),
            "--only-summary",
        ]
        print(f"Running {users} Locust users for {args.duration_seconds}s", flush=True)
        completed = subprocess.run(command, env=environment, check=False)
        stats = read_stats(stage / "final-summary.json")
        levels.append({"users": users, "exit_code": completed.returncode, **stats})
        if completed.returncode != 0:
            break
    summary = {
        "label": args.label,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "app_url": url,
        "profile": args.profile,
        "prompt": args.prompt,
        "duration_seconds_per_level": args.duration_seconds,
        "replica_count_observed": len(replicas),
        "replica_request_counts": replicas,
        "levels": levels,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--app-url", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--users", default="1,4,8,16", help="Comma-separated Locust user counts"
    )
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--probe-keys", type=int, default=60)
    parser.add_argument(
        "--prompt", default="Reply with exactly one short sentence saying hello."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        args.users = [int(value) for value in args.users.split(",")]
    except ValueError:
        parser.error("--users must be comma-separated positive integers")
    if (
        not args.users
        or any(value < 1 for value in args.users)
        or len(set(args.users)) != len(args.users)
        or args.duration_seconds < 1
        or args.timeout < 1
        or args.probe_keys < 1
    ):
        parser.error(
            "users must be distinct and positive; duration, timeout, and probe-keys must be positive"
        )
    summary = run(args)
    print(json.dumps(summary, indent=2))
    if any(
        row["exit_code"] or row["failures"] or row["incomplete"]
        for row in summary["levels"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
