#!/usr/bin/env bash
# Executes the published CLI, with one Locust runner and no custom load engine.
set -euo pipefail
umask 077

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: bash scripts/loadtest.sh EXPLICIT_PROFILE APP_NAME [RUN_NAME]" >&2
  exit 2
fi

sample_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$sample_root"
sample_profile="$1"
sample_app="$2"
sample_run="${3:-$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$sample_run" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "RUN_NAME must contain only letters, digits, hyphens, or underscores." >&2
  exit 2
fi
sample_result_dir="results/$sample_run"
sample_private_dir="private/$sample_run"
if [ -e "$sample_result_dir" ] || [ -e "$sample_private_dir" ]; then
  echo "Use a fresh RUN_NAME; existing evidence is preserved." >&2
  exit 2
fi
mkdir -p "$sample_result_dir" "$sample_private_dir"

uv run --frozen --project cli agentbricks \
  --profile "$sample_profile" --output json \
  endpoint loadtest "$sample_app" \
  --path /invocations --requests requests.json --sse \
  --concurrency 2 --max-duration 60 --max-requests 10 --timeout 50 \
  --report-dir "$sample_result_dir/report" \
  --save-responses "$sample_private_dir/responses.json" \
  > "$sample_result_dir/summary.stdout.json" \
  2> >(tee "$sample_result_dir/runner.stderr.log" >&2)

uv run --frozen python scripts/check_results.py \
  "$sample_result_dir/report/summary.json" "$sample_private_dir/responses.json"
echo "Open: $sample_root/$sample_result_dir/report/index.html"
