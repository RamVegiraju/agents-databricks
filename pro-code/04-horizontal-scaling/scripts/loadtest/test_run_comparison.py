"""Safety checks for the CLI's App instance changes."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import run_comparison
from compare import compare


class ComparisonCliTests(unittest.TestCase):
    def test_waits_for_pending_update_before_restoration(self) -> None:
        with (
            patch.object(
                run_comparison,
                "app_info",
                side_effect=[
                    {"compute_status": {"state": "UPDATING"}},
                    {"compute_status": {"state": "ACTIVE"}},
                ],
            ) as read,
            patch.object(run_comparison.time, "sleep"),
        ):
            result = run_comparison.wait_for_update_idle(
                "example-profile", "example-app", 30
            )
        self.assertEqual(read.call_count, 2)
        self.assertEqual(result["compute_status"]["state"], "ACTIVE")

    def test_update_uses_json_mask(self) -> None:
        with patch.object(run_comparison.subprocess, "run") as command:
            command.return_value.returncode = 0
            run_comparison.set_instances("example-profile", "example-app", 3, 3)
        argv = command.call_args.args[0]
        self.assertEqual(
            argv[:4], ["databricks", "apps", "create-update", "example-app"]
        )
        self.assertEqual(argv[4], "--json")
        self.assertIn("--no-wait", argv)
        self.assertEqual(
            json.loads(argv[5]),
            {
                "update_mask": "compute_min_instances,compute_max_instances",
                "app": {"compute_min_instances": 3, "compute_max_instances": 3},
            },
        )

    def test_renders_reports_and_restores_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                profile="example-profile",
                app_name="example-app",
                users=[4],
                duration_seconds=10,
                timeout=30,
                probe_keys=10,
                scale_wait_seconds=30,
                prompt="hello",
                output_dir=Path(directory) / "comparison",
                quiet_locust=True,
                leave_at_three=False,
            )
            info = {
                "compute_min_instances": 1,
                "compute_max_instances": 1,
                "url": "https://example.com",
            }
            shared = {
                "app_url": info["url"],
                "profile": args.profile,
                "prompt": args.prompt,
                "duration_seconds_per_level": args.duration_seconds,
            }
            summaries = [
                {
                    **shared,
                    "replica_count_observed": count,
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
                for count, rate in ((1, 1.0), (3, 2.0))
            ]
            with (
                patch.object(run_comparison, "parse_args", return_value=args),
                patch.object(
                    run_comparison,
                    "app_info",
                    side_effect=[
                        info,
                        {
                            **info,
                            "compute_min_instances": 3,
                            "compute_max_instances": 3,
                        },
                    ],
                ),
                patch.object(run_comparison, "set_instances") as update,
                patch.object(run_comparison, "wait_for_instances"),
                patch.object(run_comparison, "run", side_effect=summaries),
            ):
                run_comparison.main()
            self.assertEqual(
                update.call_args_list,
                [
                    call("example-profile", "example-app", 3, 3),
                    call("example-profile", "example-app", 1, 1),
                ],
            )
            self.assertIn("2.00×", (args.output_dir / "comparison.md").read_text())
            self.assertIn(
                "three-instances/users-4/locust.html",
                (args.output_dir / "index.html").read_text(),
            )

    def test_restores_original_count_when_locust_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                profile="example-profile",
                app_name="example-app",
                users=[4],
                duration_seconds=10,
                timeout=30,
                probe_keys=10,
                scale_wait_seconds=30,
                prompt="hello",
                output_dir=Path(directory) / "comparison",
                quiet_locust=True,
                leave_at_three=False,
            )
            info = {
                "compute_min_instances": 2,
                "compute_max_instances": 2,
                "url": "https://example.com",
            }
            with (
                patch.object(run_comparison, "parse_args", return_value=args),
                patch.object(
                    run_comparison,
                    "app_info",
                    side_effect=[
                        info,
                        {
                            **info,
                            "compute_min_instances": 1,
                            "compute_max_instances": 1,
                        },
                    ],
                ),
                patch.object(run_comparison, "set_instances") as update,
                patch.object(run_comparison, "wait_for_instances"),
                patch.object(
                    run_comparison, "run", side_effect=RuntimeError("load failed")
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "load failed"):
                    run_comparison.main()
            self.assertEqual(
                update.call_args_list,
                [
                    call("example-profile", "example-app", 1, 1),
                    call("example-profile", "example-app", 2, 2),
                ],
            )

    def test_comparison_renders_a_missing_level(self) -> None:
        shared = {
            "app_url": "<app-url>",
            "profile": "<profile>",
            "prompt": "hello",
            "duration_seconds_per_level": 10,
        }
        baseline = {
            **shared,
            "replica_count_observed": 1,
            "levels": [
                {
                    "users": 4,
                    "requests_per_second": 1.0,
                    "latency_ms_p95": 1000,
                    "failures": 1,
                    "incomplete": 0,
                }
            ],
        }
        scaled = {**shared, "replica_count_observed": 3, "levels": []}
        rendered = compare(baseline, scaled)
        self.assertIn("| 4 | 1.00 | n/a | n/a |", rendered)
        self.assertIn("missing stages are shown as n/a", rendered)


if __name__ == "__main__":
    unittest.main()
