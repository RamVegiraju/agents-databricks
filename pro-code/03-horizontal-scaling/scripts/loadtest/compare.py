"""Compare two Locust summary.json files from the same workload."""

import argparse
import json
from pathlib import Path


def rate(row: dict | None) -> str:
    return f"{row['requests_per_second']:.2f}" if row else "n/a"


def gain(left: dict | None, right: dict | None) -> str:
    if not left or not right or left["requests_per_second"] <= 0:
        return "n/a"
    if any(
        row["exit_code"] or row["failures"] or row["incomplete"]
        for row in (left, right)
    ):
        return "n/a"
    return f"{right['requests_per_second'] / left['requests_per_second']:.2f}x"


def seconds(milliseconds: float | None) -> str:
    return f"{milliseconds / 1000:.1f}s" if milliseconds is not None else "n/a"


def instance_count(summary: dict) -> int | None:
    """Keep archived summaries with routing probes readable."""
    return summary.get("configured_instances", summary.get("replica_count_observed"))


def terminal_report(baseline: dict, scaled: dict) -> str:
    """Summarize the completed two-App test directly in the terminal."""
    one = {row["users"]: row for row in baseline["levels"]}
    many = {row["users"]: row for row in scaled["levels"]}
    users = sorted(one.keys() | many.keys())
    width = 88
    lines = [
        "=" * width,
        "FINAL LOAD TEST REPORT — ONE VS THREE APP INSTANCES",
        "=" * width,
        f"Apps: {baseline.get('app_name', 'one instance')} (1) -> "
        f"{scaled.get('app_name', 'three instances')} (3)",
        f"Compute: {baseline.get('compute_size', 'unknown')}  |  "
        f"Duration: {baseline['duration_seconds_per_level']}s per user level per App",
        f"Ready App instances: {instance_count(baseline)} -> {instance_count(scaled)}",
        "Apps were tested sequentially at fixed instance counts.",
        "",
        f"{'Users':>5}  {'1 inst req/s':>12}  {'3 inst req/s':>12}  {'Gain':>6}  "
        f"{'p95 1':>8}  {'p95 3':>8}  {'Done 1/3':>11}  {'Failed 1/3':>10}",
        "-" * width,
    ]
    for count in users:
        left, right = one.get(count), many.get(count)
        done = f"{left['completed'] if left else '-'}/{right['completed'] if right else '-'}"
        failed = (
            f"{left['failures'] if left else '-'}/{right['failures'] if right else '-'}"
        )
        lines.append(
            f"{count:>5}  {rate(left):>12}  {rate(right):>12}  {gain(left, right):>6}  "
            f"{seconds(left['latency_ms_p95'] if left else None):>8}  "
            f"{seconds(right['latency_ms_p95'] if right else None):>8}  "
            f"{done:>11}  {failed:>10}"
        )
    lines.extend(["-" * width])
    for label, summary in (("1 instance", baseline), ("3 instances", scaled)):
        stages = summary["levels"]
        lines.append(
            f"{label}: {sum(row['completed'] for row in stages)} completed, "
            f"{sum(row['failures'] for row in stages)} failed, "
            f"{sum(row['incomplete'] for row in stages)} incomplete across {len(stages)} stage(s)"
        )
    common = one.keys() & many.keys()
    if common:
        highest = max(common)
        lines.append(
            f"At {highest} users: {rate(one[highest])} -> {rate(many[highest])} req/s "
            f"({gain(one[highest], many[highest])}); "
            f"p95 {seconds(one[highest]['latency_ms_p95'])} -> "
            f"{seconds(many[highest]['latency_ms_p95'])}."
        )
    if one.keys() != many.keys():
        lines.append(
            "Some user levels were not completed for both Apps; see n/a rows above."
        )
    lines.extend(
        [
            "Rates use completed requests / elapsed time, including the final drain.",
            "This is provisioned capacity; neither App autoscaled during the test.",
            "=" * width,
        ]
    )
    return "\n".join(lines)


def compare(baseline: dict, scaled: dict) -> str:
    for key in ("profile", "prompt", "duration_seconds_per_level"):
        if baseline.get(key) != scaled.get(key):
            raise ValueError(f"Benchmark inputs differ at {key}")
    if baseline.get("compute_size") != scaled.get("compute_size"):
        raise ValueError("Benchmark Apps use different compute sizes")
    one = {row["users"]: row for row in baseline["levels"]}
    many = {row["users"]: row for row in scaled["levels"]}
    lines = [
        f"One-instance App: {baseline['app_url']}",
        f"Three-instance App: {scaled['app_url']}",
        f"App instances: {instance_count(baseline)} → {instance_count(scaled)}",
        "",
        "| Users | Baseline full-run req/s | Scaled full-run req/s | Gain | Baseline p95 ms | Scaled p95 ms | Failures (base / scaled) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for users in sorted(one.keys() | many.keys()):
        left, right = one.get(users), many.get(users)
        stage_gain = gain(left, right).replace("x", "×")
        lines.append(
            f"| {users} | {rate(left)} | {rate(right)} | {stage_gain} | "
            f"{left['latency_ms_p95'] if left else 'n/a'} | "
            f"{right['latency_ms_p95'] if right else 'n/a'} | "
            f"{left['failures'] if left else 'n/a'} / {right['failures'] if right else 'n/a'} |"
        )
    if one.keys() != many.keys():
        lines.extend(
            [
                "",
                "Runs stopped at different user levels; missing stages are shown as n/a.",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("scaled", type=Path)
    args = parser.parse_args()
    print(
        compare(
            json.loads(args.baseline.read_text()), json.loads(args.scaled.read_text())
        )
    )


if __name__ == "__main__":
    main()
