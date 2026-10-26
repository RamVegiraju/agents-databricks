"""Run and render a live one-versus-three Databricks Apps Locust comparison."""

import argparse
import html
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from compare import compare
from run import run


def app_info(profile: str, app_name: str) -> dict:
    result = subprocess.run(
        ["databricks", "apps", "get", app_name, "--profile", profile, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def set_instances(profile: str, app_name: str, minimum: int, maximum: int) -> None:
    request = {
        "update_mask": "compute_min_instances,compute_max_instances",
        "app": {
            "compute_min_instances": minimum,
            "compute_max_instances": maximum,
        },
    }
    print(f"Setting App instances to {minimum}–{maximum}...", flush=True)
    result = subprocess.run(
        [
            "databricks",
            "apps",
            "create-update",
            app_name,
            "--json",
            json.dumps(request),
            "--no-wait",
            "--profile",
            profile,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"App update failed: {result.stderr.strip()}")


def wait_for_instances(
    profile: str, app_name: str, count: int, timeout_seconds: int
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while True:
        info = app_info(profile, app_name)
        configured = (
            info.get("compute_min_instances"),
            info.get("compute_max_instances"),
        )
        active = info.get("compute_status", {}).get("active_instances")
        running = info.get("app_status", {}).get("running_instances")
        print(
            f"App readiness: configured={configured}, active={active}, running={running}",
            flush=True,
        )
        if (
            configured == (count, count)
            and active == count
            and running == count
            and info.get("compute_status", {}).get("state") == "ACTIVE"
            and info.get("app_status", {}).get("state") == "RUNNING"
        ):
            return info
        if time.monotonic() >= deadline:
            raise TimeoutError(f"App did not reach {count} running instances")
        time.sleep(5)


def wait_for_update_idle(profile: str, app_name: str, timeout_seconds: int) -> dict:
    """Let an accepted asynchronous update settle before attempting restoration."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        info = app_info(profile, app_name)
        if info.get("compute_status", {}).get("state") != "UPDATING":
            return info
        if time.monotonic() >= deadline:
            raise TimeoutError("App update did not settle before restoration")
        time.sleep(5)


def render_report(
    output_dir: Path, baseline: dict, scaled: dict, comparison: str
) -> Path:
    rows = []
    for users in sorted(
        {row["users"] for summary in (baseline, scaled) for row in summary["levels"]}
    ):
        cells = []
        for label, summary in (("one-instance", baseline), ("three-instances", scaled)):
            stage = next(
                (row for row in summary["levels"] if row["users"] == users), None
            )
            if stage is None:
                cells.append("<td>Not run</td>")
                continue
            path = f"{label}/users-{users}/locust.html"
            cells.append(
                f'<td><a href="{html.escape(path)}">Locust HTML</a> — '
                f"{stage['requests_per_second']:.2f} req/s, "
                f"p95 {stage['latency_ms_p95']} ms, "
                f"{stage['completed']} completed, {stage['failures']} failed</td>"
            )
        rows.append(f"<tr><th scope='row'>{users}</th>{''.join(cells)}</tr>")
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>App instance comparison</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.5rem;text-align:left}}
pre{{overflow:auto;background:#f3f4f6;padding:1rem}}</style>
<h1>One versus three App instances</h1>
<p>Fixed instance counts changed by the CLI. Locust reports include latency and request charts.</p>
<table><thead><tr><th>Users</th><th>One instance</th><th>Three instances</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<h2>CLI comparison</h2><pre>{html.escape(comparison)}</pre>
</html>
"""
    report = output_dir / "index.html"
    report.write_text(page)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--users", default="1,4,8,16")
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--probe-keys", type=int, default=60)
    parser.add_argument("--scale-wait-seconds", type=int, default=600)
    parser.add_argument(
        "--prompt", default="Reply with exactly one short sentence saying hello."
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--quiet-locust",
        action="store_true",
        help="Hide periodic Locust CLI statistics",
    )
    parser.add_argument(
        "--leave-at-three",
        action="store_true",
        help="Keep three instances after a successful run",
    )
    args = parser.parse_args()
    try:
        args.users = [int(value) for value in args.users.split(",")]
    except ValueError:
        parser.error("--users must be comma-separated positive integers")
    if (
        not args.users
        or any(value < 1 for value in args.users)
        or len(set(args.users)) != len(args.users)
        or min(
            args.duration_seconds,
            args.timeout,
            args.probe_keys,
            args.scale_wait_seconds,
        )
        < 1
    ):
        parser.error(
            "users must be distinct and positive; timeouts and probe count must be positive"
        )
    if args.output_dir is None:
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
        args.output_dir = Path("results") / f"comparison-{stamp}"
    if args.output_dir.exists():
        parser.error(f"output directory already exists: {args.output_dir}")
    return args


def main() -> None:
    args = parse_args()
    initial = app_info(args.profile, args.app_name)
    original = (
        initial.get("compute_min_instances"),
        initial.get("compute_max_instances"),
    )
    if not all(isinstance(value, int) for value in original):
        raise RuntimeError("App has no readable initial instance configuration")
    if original[0] != original[1] or original[0] not in (1, 2, 3, 4, 5):
        raise RuntimeError(
            "This comparison requires an App with a fixed 1–5 instance count"
        )
    url = initial.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError("App has no HTTPS URL; deploy it before benchmarking")
    args.output_dir.mkdir(parents=True)
    print(f"App: {args.app_name}; initial instance range: {original}", flush=True)
    print("This command manually sets one instance, then three instances.", flush=True)
    success = False
    changed = False
    current = original
    try:
        summaries = []
        for count, label in ((1, "one-instance"), (3, "three-instances")):
            if current != (count, count):
                # A request may take effect even if the CLI loses its response.
                # Attempt restoration after any update attempt.
                changed = True
                set_instances(args.profile, args.app_name, count, count)
                current = (count, count)
            wait_for_instances(
                args.profile, args.app_name, count, args.scale_wait_seconds
            )
            summary = run(
                argparse.Namespace(
                    profile=args.profile,
                    app_url=url,
                    label=label,
                    users=args.users,
                    duration_seconds=args.duration_seconds,
                    timeout=args.timeout,
                    probe_keys=args.probe_keys,
                    prompt=args.prompt,
                    output_dir=args.output_dir / label,
                    live_stats=not args.quiet_locust,
                    expected_replicas=count,
                )
            )
            summaries.append(summary)
        comparison = compare(*summaries)
        (args.output_dir / "comparison.md").write_text(comparison + "\n")
        report = render_report(args.output_dir, *summaries, comparison)
        print(f"\n{comparison}\n", flush=True)
        print(f"Locust reports: {report.resolve()}", flush=True)
        if any(
            row["exit_code"] or row["failures"] or row["incomplete"]
            for summary in summaries
            for row in summary["levels"]
        ):
            raise SystemExit(
                "One or more Locust stages failed; inspect the saved reports"
            )
        success = True
    finally:
        if changed and not (args.leave_at_three and success):
            latest = wait_for_update_idle(
                args.profile, args.app_name, args.scale_wait_seconds
            )
            if (
                latest.get("compute_min_instances"),
                latest.get("compute_max_instances"),
            ) != original:
                set_instances(args.profile, args.app_name, *original)
                wait_for_instances(
                    args.profile, args.app_name, original[0], args.scale_wait_seconds
                )
                print(f"Restored original instance range: {original}", flush=True)


if __name__ == "__main__":
    main()
