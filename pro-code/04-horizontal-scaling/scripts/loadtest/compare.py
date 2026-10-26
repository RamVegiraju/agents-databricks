"""Compare two Locust summary.json files from the same workload."""

import argparse
import json
from pathlib import Path


def rate(row: dict | None) -> str:
    return f"{row['requests_per_second']:.2f}" if row else "n/a"


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
        f"Observed replicas: {baseline['replica_count_observed']} → {scaled['replica_count_observed']}",
        "",
        "| Users | Baseline full-run req/s | Scaled full-run req/s | Gain | Baseline p95 ms | Scaled p95 ms | Failures (base / scaled) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for users in sorted(one.keys() | many.keys()):
        left, right = one.get(users), many.get(users)
        a = left["requests_per_second"] if left else None
        b = right["requests_per_second"] if right else None
        gain = (
            f"{b / a:.2f}×"
            if a is not None
            and b is not None
            and a > 0
            and not any(row["failures"] or row["incomplete"] for row in (left, right))
            else "n/a"
        )
        lines.append(
            f"| {users} | {rate(left)} | {rate(right)} | {gain} | "
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
    if baseline["replica_count_observed"] != 1 or scaled["replica_count_observed"] < 3:
        lines.extend(
            [
                "",
                "Replica probe did not confirm a one-to-three change. Check Apps compute status.",
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
