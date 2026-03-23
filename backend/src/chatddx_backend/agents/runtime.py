# src/chatddx_backend/agents/runtime.py
from typing import Any, AsyncGenerator

from asgiref.sync import sync_to_async
from pydantic_ai import AgentRunResult

from chatddx_backend.agents.pydantic_ai import (
    AgentContext,
    PydanticAgent,
    build_agent,
)
from chatddx_backend.agents.state import (
    agent_spec_from_data,
    agent_spec_from_registry,
)
from chatddx_backend.agents.utils import OutputType

registry: dict[str, Any] = {}


def get_agent_sync(
    config: dict[str, Any] | str,
) -> tuple[PydanticAgent[AgentContext, OutputType], AgentContext]:
    match config:
        case str():
            agent_spec = agent_spec_from_registry(config, registry)
        case dict():
            agent_spec = agent_spec_from_data(config)

    return build_agent(agent_spec)


get_agent_async = sync_to_async(get_agent_sync, thread_sensitive=True)


def run_sync(
    config: dict[str, Any],
    prompt: str,
) -> AgentRunResult[OutputType]:
    agent, agent_context = get_agent_sync(config)
    result = agent.run_sync(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    )
    return result


async def stream_producer(
    config: dict[str, Any] | str, prompt: str
) -> AsyncGenerator[OutputType, None]:

    agent, agent_context = await get_agent_async(config)

    async with agent.run_stream(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    ) as result:
        async for chunk in result.stream_output(debounce_by=0.1):
            yield chunk


async def run_async_producer(
    config: dict[str, Any] | str, prompt: str
) -> AgentRunResult[OutputType]:

    agent, agent_context = await get_agent_async(config)

    result = await agent.run(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    )
    return result
