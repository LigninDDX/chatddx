# src/chatddx_backend/agents/session.py
from uuid import UUID

from pydantic import BaseModel

from chatddx_backend.agents.models import Session
from chatddx_backend.agents.models.session import User
from chatddx_backend.agents.schemas import (
    AgentSpec,
    SessionSpec,
    UserSpec,
)


class AgentSession(BaseModel):
    agent: AgentSpec
    session: SessionSpec


async def start(
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

    return await resume(user, session_model.uuid)


async def resume(
    user: UserSpec,
    uuid: UUID,
    agent: AgentSpec | None = None,
) -> AgentSession:

    session_model = (
        await Session.objects.select_related(
            "user",
            "user__auth_user",
            "user__default_agent",
            "user__default_agent__connection",
            "user__default_agent__sampling_params",
            "default_agent",
            "default_agent__connection",
            "default_agent__sampling_params",
        )
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
