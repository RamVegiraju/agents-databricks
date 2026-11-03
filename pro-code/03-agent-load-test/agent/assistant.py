"""Native OpenAI Agents SDK execution against a real Databricks model service."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from agents import (
    Agent,
    ModelSettings,
    RunConfig,
    RunContextWrapper,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
)
from databricks.sdk import WorkspaceClient
from databricks_openai import AsyncDatabricksOpenAI

from agent.tools import lookup_inventory

MODEL = os.environ.get("AGENT_MODEL_SERVICE_AGENT", "system.ai.claude-haiku-4-5")


@dataclass
class InventoryContext:
    """Record actual local tool calls for one invocation, without shared mutable state."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@function_tool
async def check_inventory(
    context: RunContextWrapper[InventoryContext], sku: str, destination: str
) -> str:
    """Look up available stock and estimated transit business days for a sample product.

    Args:
        sku: Product SKU, such as MX-100, SF-200, or RX-300.
        destination: Destination city, Boston or Austin.

    Returns:
        JSON facts from the local synthetic inventory, including available stock by warehouse.
    """
    facts = await asyncio.to_thread(lookup_inventory, sku, destination)
    context.context.tool_calls.append(
        {
            "tool": "check_inventory",
            "arguments": {"sku": sku, "destination": destination},
            "result": facts,
        }
    )
    return json.dumps(facts)


def configure_client() -> None:
    """Configure real model access once at startup, using the explicit profile or App identity.

    Raises:
        ValueError: If local execution has no explicitly selected Databricks profile.

    Side effects:
        Resolves Databricks credentials and configures the SDK client. Never exports credentials.
        Model calls have a 30-second transport timeout and no automatic provider retries.
    """
    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
    if not profile and not os.environ.get("DATABRICKS_APP_NAME"):
        raise ValueError("Set DATABRICKS_CONFIG_PROFILE explicitly for local real-inference runs.")
    workspace = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
    set_default_openai_client(
        AsyncDatabricksOpenAI(
            workspace_client=workspace,
            use_ai_gateway=True,
            timeout=30.0,
            max_retries=0,
        )
    )
    set_default_openai_api("chat_completions")


def start_agent(messages: list[dict[str, str]], context: InventoryContext):
    """Start a streamed native agent run with bounded turns and generation.

    Args:
        messages: Validated user messages for this independent invocation.
        context: Request-owned audit of tool calls; never reused between users.

    Returns:
        Native streamed run result, to be fully consumed by the HTTP handler.

    Side effects:
        Executes real model calls and the local read-only inventory tool. At most three
        model turns, each with at most 384 output tokens; provider retries are disabled.
        Native OpenAI tracing is disabled; this sample does not provision a trace destination.
    """
    agent = Agent[InventoryContext](
        name="Inventory fulfillment assistant",
        instructions=(
            "You assist an industrial parts distributor using SYNTHETIC demo inventory. "
            "Always call check_inventory for the requested SKU and city before answering. "
            "Use available stock after reservations. Propose the fastest feasible split shipment; "
            "do not exceed available units at any warehouse. Explicitly state any shortfall or "
            "missed requested deadline. Transit values are estimates in business days, not guarantees. "
            "Keep the answer under 120 words. Mention this is a recommendation using sample data; "
            "no reservation, order, or shipment has been created. Do not invent stock or dates."
        ),
        model=MODEL,
        tools=[check_inventory],
        model_settings=ModelSettings(max_tokens=384, tool_choice="required"),
        reset_tool_choice=True,
    )
    return Runner.run_streamed(
        agent,
        input=messages,
        context=context,
        max_turns=3,
        run_config=RunConfig(tracing_disabled=True),
    )
