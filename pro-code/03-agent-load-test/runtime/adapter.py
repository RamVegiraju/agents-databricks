"""Map managed invocations to the existing stateless inventory agent."""

import asyncio
from typing import Any

from databricks_agentkit import InvocationContext
from databricks_agentkit.openai import start_trace

from agent.assistant import MODEL, InventoryContext, start_agent

_slots = asyncio.Semaphore(2)


def _messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, dict) or set(value) != {"messages"}:
        raise ValueError("input must contain only a messages array")
    messages = value["messages"]
    if not isinstance(messages, list) or len(messages) != 1:
        raise ValueError("messages must contain exactly one user message")
    message = messages[0]
    if not isinstance(message, dict) or set(message) != {"role", "content"}:
        raise ValueError("message must contain role and content")
    content = message["content"]
    if message["role"] != "user" or not isinstance(content, str) or not 1 <= len(content) <= 2000:
        raise ValueError("message must have user role and 1 to 2000 characters of content")
    return [{"role": "user", "content": content}]


async def invoke(value: Any, context: InvocationContext) -> dict:
    """Run one inventory request and emit CLI-compatible answer and usage events."""
    async with asyncio.timeout(45):
        async with _slots:
            messages = _messages(value)
            with start_trace(
                name="inventory_invocation", inputs=messages, session_id=context.session_id
            ):
                inventory = InventoryContext()
                result = start_agent(messages, inventory)
                try:
                    async for event in result.stream_events():
                        if (
                            event.type == "raw_response_event"
                            and event.data.type == "response.output_text.delta"
                        ):
                            await context.emit({"type": "delta", "content": event.data.delta})
                    if not inventory.tool_calls:
                        raise RuntimeError("Agent finished without its required inventory tool")
                    usage = result.context_wrapper.usage
                    output = {
                        "model": MODEL,
                        "answer": str(result.final_output),
                        "usage": {
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens,
                            "model_requests": usage.requests,
                        },
                        "tool_calls": inventory.tool_calls,
                    }
                    await context.emit({"type": "run.completed", "usage": output["usage"]})
                    return output
                finally:
                    if not result.is_complete:
                        result.cancel()


async def recover(value: Any, context: InvocationContext) -> dict:
    """Replay interrupted work; the local inventory tool has no side effects."""
    return await invoke(value, context)
