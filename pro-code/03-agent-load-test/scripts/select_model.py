"""Set one existing model service consistently in the deployment and local agent."""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATTERN = re.compile(r"^system\.ai\.[a-z0-9][a-z0-9-]*$")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Existing system.ai model service with chat completions")
    args = parser.parse_args()
    if not MODEL_PATTERN.fullmatch(args.model):
        parser.error("Expected a model service name such as system.ai.claude-haiku-4-5")

    files = {
        "agent.toml": re.compile(r'(?m)^(name = ")system\.ai\.[a-z0-9-]+(")$'),
        "app.yaml": re.compile(r"(?m)^(  value: )system\.ai\.[a-z0-9-]+$"),
        "agent/assistant.py": re.compile(
            r'(?m)^(MODEL = os\.environ\.get\("AGENT_MODEL_SERVICE_AGENT", ")'
            r'system\.ai\.[a-z0-9-]+("\))$'
        ),
    }
    updates = []
    for filename, pattern in files.items():
        path = ROOT / filename
        original = path.read_text()
        replacement = (
            rf"\g<1>{args.model}\g<2>" if filename != "app.yaml" else rf"\g<1>{args.model}"
        )
        updated, count = pattern.subn(replacement, original)
        if count != 1:
            raise RuntimeError(f"Expected one model setting in {filename}; found {count}")
        updates.append((path, updated))
    for path, updated in updates:
        path.write_text(updated)
    print(f"Selected {args.model} in agent.toml, app.yaml, and agent/assistant.py")


if __name__ == "__main__":
    main()
