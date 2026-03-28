# src/chatddx_backend/agents/session.py
from uuid import UUID

from pydantic import BaseModel

from chatddx_backend.agents.models import Message, Session
from chatddx_backend.agents.models.session import User
from chatddx_backend.agents.schemas import (
    AgentSpec,
    MessageSpec,
    SessionSpec,
    UserSpec,
)


class AgentSession(BaseModel):
    agent: AgentSpec
    session: SessionSpec


async def start_session(
    user: UserSpec,
    agent: AgentSpec | None = None,
    description: str | None = None,
) -> AgentSession:

    resolved_agent = agent or user.default_agent

    session_model = await Session.objects.acreate(
        user_id=user.id,
        default_agent_id=resolved_agent.id,
        description=description,
    )

    return await resume_session(user, session_model.uuid)


async def resume_session(
    user: UserSpec,
    uuid: UUID,
    agent: AgentSpec | None = None,
) -> AgentSession:

    session_model = (
        await Session.objects.select_related()
        .prefetch_related(
            "messages",
        )
        .aget(
            uuid=uuid,
            user_id=user.id,
        )
    )

    session = SessionSpec.model_validate(session_model)

    resolved_agent = agent or session.default_agent

    return AgentSession(
        agent=resolved_agent,
        session=session,
    )


async def refresh_messages(
    agent_session: AgentSession,
) -> None:
    queryset = Message.objects.select_related().filter(
        session_id=agent_session.session.id
    )

    if len(agent_session.session.messages) > 0:
        queryset = queryset.filter(pk__gt=agent_session.session.messages[-1].id)

    messages = [obj async for obj in queryset]
    agent_session.session.messages.extend(
        [MessageSpec.model_validate(m) for m in messages]
    )


async def get_user(name: str):
    user_model = await User.objects.select_related(
        "auth_user",
        "default_agent",
        "default_agent__connection",
        "default_agent__sampling_params",
        "default_agent__output_type",
        "default_agent__tool_group",
    ).aget(auth_user__username=name)

    return UserSpec.model_validate(user_model)
