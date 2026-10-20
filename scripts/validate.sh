#!/usr/bin/env bash
# Run isolated, locked tests without calling workspace services or enabling live tests.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RUN_LIVE_TESTS=0
export AGENTBRICKS_DISABLE_TELEMETRY=1
export AGENTBRICKS_DISABLE_AGENT_HINT=1
for SAMPLE in pro-code/01-hello-memory pro-code/02-genie-supervisor pro-code/03-retail-assistant lower-code/genie-agents; do
  (
    cd "$REPO_ROOT/$SAMPLE"
    uv run --offline --locked pytest -q
    if [[ "$SAMPLE" == pro-code/* ]]; then
      uv run --offline --locked agentbricks doctor .
    fi
  )
done
