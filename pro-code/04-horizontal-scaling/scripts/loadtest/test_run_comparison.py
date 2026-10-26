"""Checks for the two ready App comparison CLI."""

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_comparison
from compare import compare


def app(name: str, count: int) -> dict:
    return {
        "name": name,
        "url": f"https://{name}.example.com",
        "compute_size": "MEDIUM",
        "compute_min_instances": count,
        "compute_max_instances": count,
        "compute_status": {"active_instances": count, "state": "ACTIVE"},
        "app_status": {"running_instances": count, "state": "RUNNING"},
    }


def summary(url: str, count: int, rate: float) -> dict:
    return {
        "app_url": url,
        "profile": "example-profile",
        "prompt": "hello",
        "duration_seconds_per_level": 10,
        "replica_count_observed": count,
        "compute_size": "MEDIUM",
        "levels": [
            {
                "users": 4,
                "requests_per_second": rate,
                "latency_ms_p95": 1000,
                "completed": 20,
                "failures": 0,
                "incomplete": 0,
                "exit_code": 0,
            }
        ],
    }


class ComparisonCliTests(unittest.TestCase):
    def test_waits_for_configured_active_and_running_count(self) -> None:
        starting = app("three", 1)
        starting["compute_min_instances"] = 3
        starting["compute_max_instances"] = 3
        with (
            patch.object(
                run_comparison, "app_info", side_effect=[starting, app("three", 3)]
            ) as read,
            patch.object(run_comparison.time, "sleep"),
        ):
            result = run_comparison.wait_for_instances(
                "example-profile", "three", 3, 30
            )
        self.assertEqual(read.call_count, 2)
        self.assertEqual(result["app_status"]["running_instances"], 3)

    def test_both_apps_are_ready_before_locust_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                profile="example-profile",
                one_app_name="one",
                three_app_name="three",
                users=[4],
                duration_seconds=10,
                timeout=30,
                probe_keys=10,
                ready_wait_seconds=30,
                prompt="hello",
                output_dir=Path(directory) / "comparison",
                quiet_locust=True,
            )
            one = app("one", 1)
            three = app("three", 3)
            events = []

            def ready(_profile, name, count, _timeout):
                events.append(f"ready-{name}")
                return one if count == 1 else three

            def load(arguments):
                events.append(f"load-{arguments.label}")
                rate = 1.0 if arguments.expected_replicas == 1 else 2.0
                return summary(arguments.app_url, arguments.expected_replicas, rate)

            with (
                patch.object(run_comparison, "parse_args", return_value=args),
                patch.object(run_comparison, "wait_for_instances", side_effect=ready),
                patch.object(run_comparison, "run", side_effect=load),
            ):
                run_comparison.main()
            self.assertEqual(
                events,
                [
                    "ready-one",
                    "ready-three",
                    "load-one-instance",
                    "load-three-instances",
                ],
            )
            self.assertIn("2.00×", (args.output_dir / "comparison.md").read_text())
            self.assertIn(
                "three-instances/users-4/locust.html",
                (args.output_dir / "index.html").read_text(),
            )

    def test_different_app_urls_compare_and_missing_level_is_marked(self) -> None:
        baseline = summary("https://one.example.com", 1, 1.0)
        scaled = summary("https://three.example.com", 3, 2.0)
        scaled["levels"] = []
        rendered = compare(baseline, scaled)
        self.assertIn("One-instance App: https://one.example.com", rendered)
        self.assertIn("Three-instance App: https://three.example.com", rendered)
        self.assertIn("| 4 | 1.00 | n/a | n/a |", rendered)

    def test_different_compute_sizes_are_rejected(self) -> None:
        baseline = summary("https://one.example.com", 1, 1.0)
        scaled = summary("https://three.example.com", 3, 2.0)
        scaled["compute_size"] = "LARGE"
        with self.assertRaisesRegex(ValueError, "different compute sizes"):
            compare(baseline, scaled)


if __name__ == "__main__":
    unittest.main()
