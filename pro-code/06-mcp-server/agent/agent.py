"""A LangGraph tool loop with MCP tools declared in agent.toml."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from databricks_agentkit import workspace_client, workspace_headers
from databricks_agentkit.langgraph import (
    checkpointer,
    configure_tracing,
    mcp_tools,
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

MODEL = resolve_model_service() or "system.ai.claude-sonnet-4-5"
SYSTEM_PROMPT = (
    "You are a research assistant. For questions about recent events, use the "
    "web_search MCP tool. Summarize what you found and include source URLs. "
    "If search is unavailable, say so rather than inventing current information."
)


class _RoutedChatDatabricks(ChatDatabricks):
    """Forward workspace routing headers when an account host needs them."""

    def _get_client_kwargs(self) -> dict[str, Any]:
        kwargs = super()._get_client_kwargs()
        if headers := workspace_headers():
            kwargs["default_headers"] = headers
        return kwargs


@lru_cache(maxsize=1)
def _app_workspace_client():
    return workspace_client()


def configure() -> None:
    """Initialize tracing after the CLI or App has set its environment."""
    configure_tracing()


def build_graph(chat_model: Any, saver: Any, tools: list[Any]) -> Any:
    """Build the model → MCP tool → model loop."""
    bound_model = chat_model.bind_tools(tools) if tools else chat_model

    async def call_model(state: MessagesState) -> dict[str, Any]:
        response = await bound_model.ainvoke(
            [SystemMessage(SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_edge(START, "agent")
    if tools:
        builder.add_node("tools", ToolNode(tools))
        builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)
    return builder.compile(checkpointer=saver)


async def create_agent_graph() -> Any:
    """Discover bound MCP tools for this request and construct the graph."""
    tools = await mcp_tools()
    model = _RoutedChatDatabricks(
        endpoint=MODEL, workspace_client=_app_workspace_client(), use_ai_gateway=True
    )
    return build_graph(model, checkpointer(), tools)


async def recovery_input(
    agent_input: Any, *, session_id: str, invocation_id: str
) -> Any:
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
    """Stream LangGraph events to the HTTP adapter."""
    graph = graph or await create_agent_graph()
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
