# src/chatddx_backend/agents/pydantic_ai/runners.py
from typing import AsyncGenerator

from pydantic_ai import AgentRunResult

from chatddx_backend.agents.pydantic_ai.agent import (
    OutputType,
    build_agent,
)
from chatddx_backend.agents.schema import AgentSpec


def run_sync(
    agent_spec: AgentSpec,
    prompt: str,
) -> AgentRunResult[OutputType]:
    agent, agent_context = build_agent(agent_spec)
    result = agent.run_sync(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    )
    return result


async def stream(
    agent_spec: AgentSpec,
    prompt: str,
) -> AsyncGenerator[OutputType, None]:
    agent, agent_context = build_agent(agent_spec)
    async with agent.run_stream(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    ) as result:
        async for chunk in result.stream_output(debounce_by=0.1):
            yield chunk


async def run_async(
    agent_spec: AgentSpec,
    prompt: str,
) -> AgentRunResult[OutputType]:
    agent, agent_context = build_agent(agent_spec)
    result = await agent.run(
        prompt,
        deps=agent_context,
        message_history=agent_context.message_history,
    )
    return result
