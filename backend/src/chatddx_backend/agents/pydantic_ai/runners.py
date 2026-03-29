# src/chatddx_backend/agents/pydantic_ai/runners.py
from typing import AsyncGenerator

from pydantic_ai import AgentRunResult, ModelResponse
from pydantic_ai.result import StreamedRunResult
from pydantic_core import to_jsonable_python

from chatddx_backend.agents.models import MessageModel, RoleChoices
from chatddx_backend.agents.pydantic_ai.context import AgentContext
from chatddx_backend.agents.schemas import AgentSpec, SessionSpec
from chatddx_backend.agents.utils import Dispatcher

from .builder import (
    OutputType,
    build_agent,
    build_output_type,
)


async def run_from_spec(
    agent_spec: AgentSpec,
    prompt: str,
    dispatcher: Dispatcher | None = None,
) -> AgentRunResult[OutputType]:

    if not dispatcher:
        dispatcher = Dispatcher()

    output_type = build_output_type(agent_spec)
    agent = build_agent(agent_spec, output_type)
    agent_context = AgentContext(agent=agent_spec, output_type=output_type)

    result = await agent.run(prompt, deps=agent_context)

    await dispatcher.publish(result)

    return result


async def stream_from_session(
    session: SessionSpec,
    prompt: str,
    dispatcher: Dispatcher | None = None,
    agent_spec: AgentSpec | None = None,
) -> AsyncGenerator[tuple[ModelResponse, bool], None]:

    if not dispatcher:
        dispatcher = Dispatcher()

    if not agent_spec:
        agent_spec = session.default_agent

    dispatcher.subscribe(
        on_result(
            session.id,
            agent_spec.id,
        )
    )

    output_type = build_output_type(agent_spec)

    agent_context = AgentContext(
        agent=agent_spec,
        output_type=output_type,
        session=session,
    )

    agent = build_agent(
        agent_spec,
        output_type,
    )

    async with agent.run_stream(
        prompt,
        deps=agent_context,
        message_history=[m.payload for m in session.messages],
    ) as result:
        async for chunk in result.stream_responses(debounce_by=0.1):
            yield chunk

        await dispatcher.publish(result)


async def run_from_session(
    session: SessionSpec,
    prompt: str,
    dispatcher: Dispatcher | None = None,
    agent_spec: AgentSpec | None = None,
) -> AgentRunResult[OutputType]:

    if not dispatcher:
        dispatcher = Dispatcher()
    if not agent_spec:
        agent_spec = session.default_agent

    dispatcher.subscribe(
        on_result(
            session.id,
            agent_spec.id,
        )
    )

    output_type = build_output_type(agent_spec)

    agent = build_agent(
        agent_spec,
        output_type,
    )

    agent_context = AgentContext(
        agent=agent_spec,
        output_type=output_type,
        session=session,
    )

    result = await agent.run(
        prompt,
        deps=agent_context,
        message_history=[m.payload for m in session.messages],
    )

    await dispatcher.publish(result)

    return result


def on_result(session_id: int, agent_id: int):
    async def _on_result(result: AgentRunResult | StreamedRunResult):
        messages = result.new_messages()
        messages_to_create: list[MessageModel] = []

        for msg in messages:
            match msg.kind:
                case "response":
                    role = RoleChoices.ASSISTANT
                case "request":
                    kind: str = msg.parts[0].part_kind
                    role = _request_role(kind)

            messages_to_create.append(
                MessageModel(
                    agent_id=agent_id,
                    session_id=session_id,
                    kind=msg.kind,
                    run_id=result.run_id,
                    role=role,
                    payload=to_jsonable_python(msg),
                    timestamp=msg.timestamp,
                )
            )

        if messages_to_create:
            await MessageModel.objects.abulk_create(messages_to_create)

    return _on_result


def _request_role(kind: str) -> RoleChoices | None:
    match kind:
        case "user-prompt":
            return RoleChoices.USER
        case "system-prompt":
            return RoleChoices.SYSTEM
        case "tool-return":
            return RoleChoices.TOOL
        case _:
            raise ValueError(f"unexpected kind '{kind}'")
