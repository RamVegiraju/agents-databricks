#!/usr/bin/env bash
# Run isolated tests from frozen locks without calling workspace services.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RUN_LIVE_TESTS=0
export AGENTBRICKS_DISABLE_TELEMETRY=1
export AGENTBRICKS_DISABLE_AGENT_HINT=1
for SAMPLE in pro-code/01-agentbricks-cli pro-code/02-agent-memory pro-code/03-horizontal-scaling pro-code/04-genie-supervisor pro-code/05-mcp-server pro-code/06-retail-assistant lower-code/genie-agents; do
  (
    cd "$REPO_ROOT/$SAMPLE"
    uv run --frozen pytest -q
    if [[ "$SAMPLE" == pro-code/* ]]; then
      uv run --frozen agentbricks doctor .
    fi
  )
done
(
  cd "$REPO_ROOT/pro-code/03-horizontal-scaling/scripts/loadtest"
  uv run --frozen python -m unittest discover -p 'test_*.py'
)
