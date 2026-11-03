# What the managed agent returns

The sample produces an **agent invocation response** and a **load-test report**.
Actual wording, token counts, and timings vary by run.

## One nonstreamed invocation

Send `POST /api/invocations` with a fresh UUID and a stable session ID:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "session_id": "demo-session",
  "input": {
    "messages": [
      {"role": "user", "content": "Can we fulfill 18 MX-100 units to Boston in one business day?"}
    ]
  },
  "stream": false
}
```

The managed runtime wraps the agent result under `output`:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "status": "completed",
  "output": {
    "model": "system.ai.claude-haiku-4-5",
    "answer": "A recommendation based on sample inventory...",
    "usage": {
      "input_tokens": 500,
      "output_tokens": 150,
      "total_tokens": 650,
      "model_requests": 2
    },
    "tool_calls": [
      {
        "tool": "check_inventory",
        "arguments": {"sku": "MX-100", "destination": "Boston"},
        "result": {"sku": "MX-100", "destination": "Boston", "warehouses": []}
      }
    ]
  }
}
```

These values are illustrative, including the abbreviated tool result. Run
`scripts/smoke.py` to save and check an actual response in `private/`.

With `"stream": true`, the runtime sends SSE `delta` events as answer text arrives
and a `run.completed` event with usage. It stores the final result and events for
`GET /api/invocations/{id}` and `GET /api/invocations/{id}/events`.

## Load-test report

The published CLI writes `results/<run>/report/index.html`, CSV files, and
`summary.json`. Its JSON summary includes the request counts, observed peak in
flight, successful requests per second, latency percentiles, answer-text TTFT,
token usage coverage, and errors. `scripts/check_results.py` compares that summary
with the private response capture and confirms all three workload cases ran.

The CLI also prints the summary to stdout. A run with `--max-requests 10` can end
before 60 seconds when all ten requests finish; omit that flag for a full minute
of request dispatch.
