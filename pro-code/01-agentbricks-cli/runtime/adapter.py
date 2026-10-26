"""Translate DurableAgentServer invocations to LangGraph input and output."""

from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

from databricks_agentkit import InvocationContext
from databricks_agentkit.langgraph.responses import checkpointed_messages
from databricks_agentkit.langgraph.session_store import thread_config
from langchain_core.messages import AIMessageChunk

from agent.agent import create_agent_graph, recovery_input, run_agent


def _messages(value: Any) -> dict[str, list]:
    if not isinstance(value, dict) or not isinstance(value.get("messages"), list):
        raise ValueError("input must be an object containing a messages list")
    return {"messages": value["messages"]}


def _session_id(context: InvocationContext) -> str:
    if not isinstance(context.session_id, str) or not context.session_id:
        raise ValueError("session_id must be a non-empty top-level invocation field")
    return context.session_id


async def invoke(value: Any, context: InvocationContext) -> dict:
    return await _invoke_agent(_messages(value), context)


async def recover(value: Any, context: InvocationContext) -> dict:
    agent_input = await recovery_input(
        _messages(value),
        session_id=_session_id(context),
        invocation_id=context.invocation_id,
    )
    return await _invoke_agent(agent_input, context)


async def _invoke_agent(agent_input: Any, context: InvocationContext) -> dict:
    session_id = _session_id(context)
    outputs = []
    graph = None
    if agent_input is None:
        graph = create_agent_graph()
        outputs = [
            {"type": "message", "message": message.model_dump()}
            for message in await checkpointed_messages(
                graph, thread_config(session_id), context.invocation_id
            )
        ]
    async for event in _serialize_events(
        run_agent(
            agent_input,
            session_id=session_id,
            invocation_id=context.invocation_id,
            graph=graph,
        )
    ):
        await context.emit(event)
        if event["type"] == "message":
            outputs.append(event)
    return {"output": [event["message"] for event in outputs], "status": "completed"}


async def _serialize_events(
    stream: AsyncIterator[Any],
) -> AsyncGenerator[dict, None]:
    async for mode, payload in stream:
        if mode == "updates":
            for node_data in payload.values():
                messages = (
                    node_data.get("messages", []) if isinstance(node_data, dict) else []
                )
                for message in messages:
                    yield {"type": "message", "message": message.model_dump()}
        elif mode == "messages":
            chunk = payload[0]
            if isinstance(chunk, AIMessageChunk) and (content := chunk.content):
                yield {"type": "delta", "content": content, "id": chunk.id}
