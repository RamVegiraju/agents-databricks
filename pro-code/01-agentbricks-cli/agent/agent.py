"""A small LangGraph tool loop, independent of the HTTP server."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from databricks_agentkit import workspace_client, workspace_headers
from databricks_agentkit.langgraph import (
    checkpointer,
    configure_tracing,
    start_trace,
    thread_config,
)
from databricks_agentkit.langgraph.session_store import (
    invocation_id_from_metadata,
    invocation_metadata,
)
from databricks_agentkit.runtime.tool_manifest import resolve_model_service
from databricks_langchain import ChatDatabricks
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.tools import get_current_time

MODEL = resolve_model_service() or "system.ai.claude-sonnet-4-5"
SYSTEM_PROMPT = "You are a helpful assistant. Use get_current_time for UTC time questions."


class _RoutedChatDatabricks(ChatDatabricks):
    """Include workspace routing headers when the account host needs them."""

    def _get_client_kwargs(self) -> dict[str, Any]:
        kwargs = super()._get_client_kwargs()
        if headers := workspace_headers():
            kwargs["default_headers"] = headers
        return kwargs


def build_graph(chat_model: Any, saver: Any) -> Any:
    """Construct the model → tool → model loop with injectable dependencies."""
    tools = [get_current_time]
    bound_model = chat_model.bind_tools(tools)

    async def call_model(state: MessagesState) -> dict[str, Any]:
        response = await bound_model.ainvoke(
            [SystemMessage(SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=saver)


def configure() -> None:
    """Initialize tracing after CLI or Apps has provided environment settings."""
    configure_tracing()


@lru_cache(maxsize=1)
def _app_workspace_client():
    """Reuse the App identity client across requests in this process."""
    return workspace_client()


def create_agent_graph() -> Any:
    model = _RoutedChatDatabricks(
        endpoint=MODEL, workspace_client=_app_workspace_client(), use_ai_gateway=True
    )
    return build_graph(model, checkpointer())


async def recovery_input(
    agent_input: Any, *, session_id: str, invocation_id: str
) -> Any:
    """Resume a checkpoint from this invocation; otherwise replay its original input."""
    checkpoint = await checkpointer().aget_tuple(thread_config(session_id))
    if checkpoint and invocation_id_from_metadata(checkpoint.metadata) == invocation_id:
        return None
    return agent_input


async def run_agent(
    agent_input: Any,
    *,
    session_id: str,
    invocation_id: str,
    graph: Any = None,
) -> AsyncGenerator[Any, None]:
    """Stream native LangGraph events for the runtime adapter."""
    graph = graph or create_agent_graph()
    config = thread_config(session_id)
    config["metadata"] = invocation_metadata(invocation_id)
    with start_trace(name="invoke", inputs=agent_input, session_id=session_id) as span:
        last_update: Any = None
        async for event in graph.astream(
            input=agent_input,
            config=config,
            stream_mode=["updates", "messages"],
            durability="sync",
        ):
            if event[0] == "updates":
                last_update = event[1]
            yield event
        if span is not None and last_update is not None:
            span.set_outputs(last_update)
