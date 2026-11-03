"""Send exactly one real, nonstreamed request with the published CLI and verify tool evidence."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def main() -> None:
    """Save one private CLI response and validate the actual inventory tool audit.

    Side effects:
        Sends one real agent request; creates a new 0600 evidence file. Does not retry.
        Raises on failed HTTP/agent execution or an incorrect/missing tool result.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", help="Explicit user-selected Databricks CLI profile")
    parser.add_argument("app", help="Deployed sample App name")
    parser.add_argument("output", type=Path, help="New private evidence filename")
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        parser.error("Output must be a new file in an existing directory.")
    body = {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Can we fulfill 18 MX-100 units to Boston in one business day? Give the fastest split plan.",
                }
            ]
        },
        "stream": False,
    }
    command = [
        "uv",
        "run",
        "--frozen",
        "--project",
        "cli",
        "agentbricks",
        "--profile",
        args.profile,
        "--output",
        "json",
        "endpoint",
        "invoke",
        args.app,
        "--path",
        "/api/invocations",
        "--timeout",
        "50",
        "--json",
        json.dumps(body),
    ]
    child_env = os.environ.copy()
    child_env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(command, text=True, capture_output=True, check=True, env=child_env)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(result.stdout)
    response = json.loads(result.stdout)
    # CLI JSON rendering may include an HTTP envelope; preserve that original evidence above.
    payload = response.get("body", response)
    assert payload["status"] == "completed", payload
    output = payload["output"]
    assert output["answer"].strip(), payload
    tool = output["tool_calls"][0]
    assert tool["tool"] == "check_inventory", tool
    assert tool["result"]["sku"] == "MX-100", tool
    assert tool["result"]["destination"] == "Boston", tool
    assert tool["result"]["warehouses"][0]["available_units"] == 8, tool
    print(
        json.dumps(
            {
                "status": "passed",
                "evidence": str(args.output),
                "model": output["model"],
                "model_requests": output["usage"]["model_requests"],
                "tool_calls": len(output["tool_calls"]),
                "answer": output["answer"],
            },
            indent=2,
        )
    )
    if result.stderr:
        print(result.stderr, file=sys.stderr)


if __name__ == "__main__":
    main()
