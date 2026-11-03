"""Verify agreement between native loadtest summary and private response capture, without inference."""

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("responses", type=Path)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    responses = json.loads(args.responses.read_text())
    counts = summary["counts"]
    assert summary["outcome"] == "completed", summary
    assert counts["started"] == counts["completed"] == counts["succeeded"] > 0, counts
    assert counts["started"] <= 10, counts
    assert counts["failed"] == counts["incomplete"] == 0, counts
    assert 0 < summary["observed_peak_in_flight"] <= 2, summary
    observations = responses["observations"]
    assert len(observations) == counts["succeeded"], (len(observations), counts)
    assert responses["case_count"] == 3, responses["case_count"]
    assert {row["case_index"] for row in observations} == {0, 1, 2}, "Missing workload case"
    assert all(row["outputs"] for row in observations), "Missing captured answers"
    ids = [row["inputs"]["id"] for row in observations]
    assert len(set(ids)) == len(ids), "Repeated invocation identities"
    assert all("{{" not in identifier for identifier in ids), "Unexpanded request placeholders"
    assert summary["ttft_coverage"]["measured"] == counts["succeeded"], summary["ttft_coverage"]
    assert summary["usage"]["observed_successes"] == counts["succeeded"], summary["usage"]
    assert summary["usage"]["output_tokens"] > 0, summary["usage"]
    print(
        json.dumps(
            {
                "status": "passed",
                "successful_requests": counts["succeeded"],
                "per_case": dict(Counter(row["case_index"] for row in observations)),
                "unique_invocations": len(set(ids)),
                "user_sessions": len({row["inputs"]["session_id"] for row in observations}),
                "note": "Evidence consistency only; not an LLM quality evaluation or capacity claim.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
