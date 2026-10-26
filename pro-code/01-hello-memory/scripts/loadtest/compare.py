"""Compare two Locust summary.json files from the same App and workload."""

import argparse
import json
from pathlib import Path


def compare(baseline: dict, scaled: dict) -> str:
    for key in ("app_url", "profile", "prompt", "duration_seconds_per_level"):
        if baseline.get(key) != scaled.get(key):
            raise ValueError(f"Benchmark inputs differ at {key}")
    one = {row["users"]: row for row in baseline["levels"]}
    many = {row["users"]: row for row in scaled["levels"]}
    if one.keys() != many.keys():
        raise ValueError("Locust user levels differ")
    lines = [
        f"App: {baseline['app_url']}",
        f"Observed replicas: {baseline['replica_count_observed']} → {scaled['replica_count_observed']}",
        "",
        "| Users | Baseline full-run req/s | Scaled full-run req/s | Gain | Baseline p95 ms | Scaled p95 ms | Failures (base / scaled) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for users in sorted(one):
        left, right = one[users], many[users]
        a, b = left["requests_per_second"], right["requests_per_second"]
        gain = (
            f"{b / a:.2f}×"
            if a
            and not any(row["failures"] or row["incomplete"] for row in (left, right))
            else "n/a"
        )
        lines.append(
            f"| {users} | {a:.2f} | {b:.2f} | {gain} | "
            f"{left['latency_ms_p95']} | {right['latency_ms_p95']} | "
            f"{left['failures']} / {right['failures']} |"
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
