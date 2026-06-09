# src/chatddx/django/runtime/runners.py
import uuid
from collections.abc import AsyncGenerator

from django.utils import timezone
from pydantic_ai import AgentRunResult, ModelRequest, ModelResponse
from pydantic_ai.result import StreamedRunResult
from pydantic_core import to_jsonable_python

from chatddx.core.choices import MessageKindChoices, RoleChoices
from chatddx.history.models import MessageModel
from chatddx.history.schemas import SessionSpec
from chatddx.repo.trail_specs import AgentSpec
from chatddx.runtime.context import AgentContext, OutputType
from chatddx.utils import Dispatcher

from .builder import (
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
        agent_spec = session.default_agent.target

    _ = dispatcher.subscribe(
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
        message_history=get_message_history(session),
    ) as result:
        async for msg in result.stream_response(debounce_by=0.1):
            is_last = msg.state != "incomplete"
            yield msg, is_last

        await dispatcher.publish(result)


def get_message_history(session: SessionSpec):
    return [
        m.payload
        for m in session.messages
        if isinstance(m.payload, (ModelResponse, ModelRequest))
    ]


async def run_from_session(
    session: SessionSpec,
    prompt: str,
    dispatcher: Dispatcher | None = None,
    agent_spec: AgentSpec | None = None,
    api_key: str | None = None,
) -> AgentRunResult[OutputType]:

    if not dispatcher:
        dispatcher = Dispatcher()

    if not agent_spec:
        agent_spec = session.default_agent.target

    _ = dispatcher.subscribe(
        on_result(
            session.id,
            agent_spec.id,
        )
    )
    _ = dispatcher.subscribe(
        on_prompt(
            session.id,
            agent_spec.id,
        )
    )
    _ = dispatcher.subscribe(
        on_error(
            session.id,
            agent_spec.id,
        )
    )

    await dispatcher.publish(prompt)

    output_type = build_output_type(agent_spec)

    agent = build_agent(
        agent_spec=agent_spec,
        output_type=output_type,
        api_key=api_key,
    )

    agent_context = AgentContext(
        agent=agent_spec,
        output_type=output_type,
        session=session,
    )

    try:
        result = await agent.run(
            prompt,
            deps=agent_context,
            message_history=get_message_history(session),
        )

        await dispatcher.publish(result)
        return result

    except Exception as e:
        await dispatcher.publish(e)
        raise e


def on_prompt(session_id: int, agent_id: int):
    async def _on_prompt(prompt: str):
        _ = await MessageModel.objects.acreate(
            agent_id=agent_id,
            session_id=session_id,
            kind="prompt",
            run_id=uuid.UUID(int=0),
            role=RoleChoices.USER,
            payload={"content": prompt},
            timestamp=timezone.now(),
        )

    return _on_prompt


def on_error(session_id: int, agent_id: int):
    async def _on_error(error: Exception):
        error_message = f"Agent execution failed: {type(error).__name__} - {str(error)}"

        _ = await MessageModel.objects.acreate(
            agent_id=agent_id,
            session_id=session_id,
            kind="error",
            run_id=uuid.UUID(int=0),
            role=RoleChoices.SYSTEM,
            payload={"error_type": type(error).__name__, "content": error_message},
            timestamp=timezone.now(),
        )

    return _on_error


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
            _ = await MessageModel.objects.abulk_create(messages_to_create)

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
