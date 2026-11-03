# What the final output looks like

The sample has two outputs: the **agent API response** and the **loadtest performance report**.
The JSON below is recorded real inference from the local smoke request on November 2, 2026.
The SSE and export snippets farther down describe their shape using explicit placeholders.
Measured performance and hosting evidence are recorded in `VALIDATION.md`.

## Agent API

Send `POST /invocations` with:

```json
{
  "input": [{"role": "user", "content": "Can we fulfill 18 MX-100 units to Boston in one business day? Give the fastest split plan."}],
  "stream": false
}
```

The JSON response contains `id`, `status`, `model`, `output`, `usage`, and `tool_calls`.
Recorded response (the full tool audit is in the private smoke evidence):

```json
{
  "id": "17d0adbe-ff1c-4496-8141-3fd58208978a",
  "status": "completed",
  "model": "system.ai.claude-haiku-4-5",
  "output": "**Recommendation (Sample Data Only)**\n\nNo, 18 units cannot ship to Boston in one business day. Here's the fastest split plan:\n\n- **Boston warehouse:** 8 units → 1 business day\n- **Chicago warehouse:** 10 units → 2 business days\n\n**Total: 18 units fulfilled**\n\nYou'll receive 8 units on day 1 and 10 units on day 2. This misses your one-day deadline by one shipment. The remaining Chicago stock (5 units) stays available.\n\n*This is a recommendation using synthetic demo data. No reservation, order, or shipment has been created.*",
  "usage": {
    "input_tokens": 1903,
    "output_tokens": 206,
    "total_tokens": 2109,
    "model_requests": 2
  }
}
```

`tool_calls` records actual execution, including `check_inventory` arguments and returned
warehouse facts. `usage` contains the SDK's accumulated `input_tokens`, `output_tokens`,
`total_tokens`, and `model_requests` across the whole agent run. The recorded smoke used two real model calls and one actual local tool execution.

With `"stream": true`, the same endpoint emits SSE:

```text
data: {"type":"response.created","response":{"id":"<invocation UUID>"}}

data: {"type":"response.output_text.delta","delta":"We can fulfill "}

data: {"type":"response.output_text.delta","delta":"8 of the 18 units..."}

data: {"type":"response.completed","response":{"id":"<invocation UUID>","status":"completed","output":"<complete real answer>","model":"<actual model service>","usage":{"input_tokens":"<actual integer>","output_tokens":"<actual integer>","total_tokens":"<actual integer>","model_requests":"<actual integer>"},"tool_calls":["<actual tool audit objects>"]}}
```

Angle-bracket values above describe fields; they are not literal runtime values. The terminal
event represents completion of the full tool/model execution. The API does not return `202`
and schedule background work. Failures emit `response.failed`, which the native CLI treats
as a failed request even if the HTTP stream initially returned status 200.

## Loadtest JSON and HTML

`agentbricks --output json endpoint loadtest ...` prints one native summary object with
these fields, and `--report-dir` writes that same object to `summary.json`:

| Field | Meaning |
| --- | --- |
| `schema_version` | Native summary schema version, currently 1 |
| `workload` | Concurrency, dispatch-duration limit, request cap, case count, excluded warm-up count |
| `outcome` | Lifecycle completion; inspect failure counts as well |
| `counts` | Started, completed, succeeded, failed, incomplete |
| `observed_peak_in_flight` | Observed simultaneous requests |
| `elapsed_seconds_including_drain` | Measured elapsed time including in-flight drain |
| `completed_rps`, `successful_rps` | Completed/successful requests divided by elapsed time |
| `latency_ms.successful` | Successful-response min, mean, max, p50, p95, p99 |
| `latency_ms.all_completed` | Same timing summary including failed completions |
| `ttft_ms`, `ttft_coverage` | Time to first nonempty answer-text delta, and observed/unknown coverage |
| `usage` | Explicit output-token totals and observed-success coverage |
| `errors` | Error categories and counts |
| `generator_cpu_warning` | Whether Locust detected high CPU on the generator |

The HTML report shows these metrics and links to the native Locust charts and CSV files.
The three workload cases are cycled in order. A run that reaches the ten-request cap with
no failures would have ten successful captured answers, with an additional warm-up excluded
from all measured counts. A duration-limited run can finish with fewer than ten requests.

The private `--save-responses` export has this schema:

```json
{
  "schema_version": 1,
  "case_count": 3,
  "observations": [
    {
      "case_index": 0,
      "inputs": {"id": "<fresh UUID>", "session_id": "<user UUID>", "input": ["<actual input message>"], "stream": true},
      "outputs": "<accumulated real answer text>",
      "trace_id": null
    }
  ]
}
```

`case_index` is zero-based. The real export includes every successful measured response.
`trace_id` stays null because this sample does not configure tracing. Export consistency
checks are separate from semantic answer quality; the sample does not run scorers.

## Recorded loadtest summary

Hosted native output, without edits:

```json
{
  "schema_version": 1,
  "workload": {
    "concurrency": 2,
    "duration_seconds": 60,
    "max_requests": 10,
    "cases": 3,
    "warmup_requests": 1
  },
  "outcome": "completed",
  "counts": {
    "started": 10,
    "completed": 10,
    "succeeded": 10,
    "failed": 0,
    "incomplete": 0
  },
  "observed_peak_in_flight": 2,
  "elapsed_seconds_including_drain": 16.07549612497678,
  "completed_rps": 0.6220647824649608,
  "successful_rps": 0.6220647824649608,
  "error_rate": 0.0,
  "latency_ms": {
    "all_completed": {
      "count": 10,
      "min": 2633.4730829985347,
      "mean": 3176.1612080968916,
      "max": 4758.243582997238,
      "p50": 2800,
      "p90": 4800,
      "p95": 4800,
      "p99": 4800
    },
    "successful": {
      "count": 10,
      "min": 2633.4730829985347,
      "mean": 3176.1612080968916,
      "max": 4758.243582997238,
      "p50": 2800,
      "p90": 4800,
      "p95": 4800,
      "p99": 4800
    }
  },
  "ttft_ms": {
    "count": 10,
    "min": 1640.6462079903577,
    "mean": 1996.6962540056556,
    "max": 3827.1073329960927,
    "p50": 1700,
    "p90": 3800,
    "p95": 3800,
    "p99": 3800
  },
  "ttft_coverage": {
    "measured": 10,
    "unknown": 0,
    "eligible_successes": 10
  },
  "usage": {
    "observed_successes": 10,
    "eligible_successes": 10,
    "output_tokens": 2109
  },
  "errors": {},
  "generator_cpu_warning": false
}
```
