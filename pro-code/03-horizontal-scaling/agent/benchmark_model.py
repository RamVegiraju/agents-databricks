"""Synthetic model for measuring App capacity without model-service quotas."""

import hashlib
import time
from typing import Any

from langchain_core.messages import AIMessage


class BenchmarkModel:
    """Exercise the real graph with a bounded amount of per-invocation CPU work."""

    def __init__(self, cpu_ms: int) -> None:
        if not 0 <= cpu_ms <= 1000:
            raise ValueError("SCALING_BENCHMARK_CPU_MS must be between 0 and 1000")
        self.cpu_ms = cpu_ms

    def bind_tools(self, tools: list[Any]) -> "BenchmarkModel":
        return self

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        # Deliberately occupy one worker's event loop to model per-request CPU work.
        deadline = time.perf_counter() + self.cpu_ms / 1000
        digest = b"agent-bricks-scaling-benchmark"
        while time.perf_counter() < deadline:
            digest = hashlib.sha256(digest).digest()
        return AIMessage(content=f"Hello from the benchmark agent. {digest[0]:02x}")
