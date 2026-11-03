"""A synchronous HTTP agent API with optional SSE; completion includes the whole tool/model run."""

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Literal
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from agent.assistant import MODEL, InventoryContext, configure_client, start_agent

logger = logging.getLogger(__name__)


class UserMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user"]
    content: str = Field(min_length=1, max_length=2000)


class InvocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()), max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    input: list[UserMessage] = Field(min_length=1, max_length=1)
    stream: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(configure_client)
    app.state.slots = asyncio.Semaphore(2)
    yield


app = FastAPI(title="Inventory fulfillment agent — Agent Bricks loadtest sample", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Report process readiness without invoking a model or tool."""
    return {"status": "ok", "model": MODEL, "inventory": "synthetic"}


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def run_events(body: InvocationRequest, request: Request) -> AsyncIterator[dict]:
    """Consume one real agent run, reporting answer deltas and a terminal result.

    Args:
        body: Validated input; id and session_id are correlation fields only, not durable state.
        request: HTTP request used to detect disconnects and access the two-invocation semaphore.

    Yields:
        Responses-style SSE objects. Terminal response.completed includes accumulated SDK usage
        and an audit of actual tool calls. Errors yield response.failed and no success event.

    Side effects:
        Makes real model calls, reads synthetic local data, and logs content-free failures.
        Total invocation deadline is 45 seconds, including semaphore waiting and model/tool work.
        Client disconnects cancel remaining local work; provider work already accepted may bill.
    """
    result = None
    try:
        async with asyncio.timeout(45):
            async with request.app.state.slots:
                context = InventoryContext()
                result = start_agent([message.model_dump() for message in body.input], context)
                yield {"type": "response.created", "response": {"id": body.id}}
                async for event in result.stream_events():
                    if await request.is_disconnected():
                        return
                    if event.type == "raw_response_event":
                        data = event.data
                        if data.type == "response.output_text.delta":
                            yield {"type": data.type, "delta": data.delta}
                if not context.tool_calls:
                    raise RuntimeError(
                        "Agent finished without executing its required inventory tool."
                    )
                usage = result.context_wrapper.usage
                yield {
                    "type": "response.completed",
                    "response": {
                        "id": body.id,
                        "status": "completed",
                        "model": MODEL,
                        "output": str(result.final_output),
                        "usage": {
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens,
                            "model_requests": usage.requests,
                        },
                        "tool_calls": context.tool_calls,
                    },
                }
    except Exception as error:
        logger.error("Agent invocation failed: %s", type(error).__name__)
        yield {"type": "response.failed", "error": {"code": "AGENT_EXECUTION_FAILED"}}
    finally:
        if result is not None and not result.is_complete:
            result.cancel()
            with suppress(asyncio.CancelledError, Exception):
                async for _ in result.stream_events():
                    pass


@app.post("/invocations")
async def invocations(body: InvocationRequest, request: Request):
    """Return the complete agent execution, as streamed events or one final JSON response."""
    if body.stream:

        async def stream() -> AsyncIterator[str]:
            async for event in run_events(body, request):
                yield sse(event)

        return StreamingResponse(stream(), media_type="text/event-stream")
    async for event in run_events(body, request):
        if event["type"] == "response.completed":
            return JSONResponse(event["response"])
        if event["type"] == "response.failed":
            return JSONResponse(event, status_code=502)
    return JSONResponse({"error": {"code": "INCOMPLETE_AGENT_EXECUTION"}}, status_code=502)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("DATABRICKS_APP_PORT", os.environ.get("PORT", "8000"))),
    )
