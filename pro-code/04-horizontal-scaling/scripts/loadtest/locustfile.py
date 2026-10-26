"""Locust workload for a complete, foreground DurableAgentServer invocation."""

import json
import os
import time
from pathlib import Path
from uuid import uuid4

from locust import HttpUser, constant, events, task

_TOKEN = os.environ["APP_BEARER_TOKEN"]
_PROMPT = os.environ.get(
    "LOADTEST_PROMPT", "Reply with exactly one short sentence saying hello."
)
_TIMEOUT = float(os.environ.get("LOADTEST_TIMEOUT", "120"))
_STARTED = 0
_START_TIME = None


@events.test_start.add_listener
def start(environment, **kwargs) -> None:
    global _START_TIME
    _START_TIME = time.perf_counter()


@events.quitting.add_listener
def save_final_summary(environment, **kwargs) -> None:
    stats = environment.stats.total
    elapsed = max(time.perf_counter() - (_START_TIME or time.perf_counter()), 0.001)
    completed = stats.num_requests
    incomplete = max(_STARTED - completed, 0)
    summary = {
        "started": _STARTED,
        "completed": completed,
        "failures": stats.num_failures,
        "incomplete": incomplete,
        "elapsed_seconds_including_drain": elapsed,
        "requests_per_second": completed / elapsed,
        "latency_ms_p50": stats.get_response_time_percentile(0.5)
        if completed
        else None,
        "latency_ms_p95": stats.get_response_time_percentile(0.95)
        if completed
        else None,
        "latency_ms_mean": stats.avg_response_time if completed else None,
    }
    Path(os.environ["LOADTEST_SUMMARY_FILE"]).write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    if (not completed or incomplete) and environment.process_exit_code is None:
        environment.process_exit_code = 1


class AgentUser(HttpUser):
    wait_time = constant(0)

    @task
    def invoke(self) -> None:
        global _STARTED
        # One new conversation per invocation avoids session serialization and growing context.
        session_id = str(uuid4())
        body = {
            "id": str(uuid4()),
            "session_id": session_id,
            "input": {"messages": [{"role": "user", "content": _PROMPT}]},
            "background": False,
            "stream": False,
        }
        _STARTED += 1
        with self.client.post(
            "/api/invocations",
            json=body,
            headers={"Authorization": f"Bearer {_TOKEN}", "X-Routing-Key": session_id},
            name="agent invocation",
            timeout=_TIMEOUT,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            try:
                result = response.json()
            except ValueError:
                response.failure("Invalid JSON")
                return
            output = result.get("output") if isinstance(result, dict) else None
            if (
                not isinstance(result, dict)
                or result.get("id") != body["id"]
                or result.get("status") != "completed"
                or not isinstance(output, dict)
                or output.get("status") != "completed"
            ):
                response.failure("Invocation did not complete")
