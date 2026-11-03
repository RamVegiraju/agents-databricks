#!/usr/bin/env bash
# Run isolated tests from frozen locks without calling workspace services.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RUN_LIVE_TESTS=0
export AGENTBRICKS_DISABLE_TELEMETRY=1
export AGENTBRICKS_DISABLE_AGENT_HINT=1
for SAMPLE in pro-code/01-agentbricks-cli pro-code/02-agent-memory pro-code/03-agent-load-test pro-code/04-horizontal-scaling pro-code/05-genie-supervisor pro-code/06-mcp-server pro-code/07-retail-assistant lower-code/genie-agents; do
  (
    cd "$REPO_ROOT/$SAMPLE"
    if [[ "$SAMPLE" == pro-code/03-agent-load-test && ! -f uv.lock ]]; then
      uv sync --default-index https://pypi.org/simple
    fi
    uv run --frozen python -m pytest -q
    if [[ "$SAMPLE" == pro-code/* && "$SAMPLE" != pro-code/03-agent-load-test ]]; then
      uv run --frozen python -c 'from databricks_agentbricks.cli.app import main; main()' doctor .
    fi
  )
done
(
  cd "$REPO_ROOT/pro-code/04-horizontal-scaling/scripts/loadtest"
  uv run --frozen python -m unittest discover -p 'test_*.py'
)
