# src/chatddx_backend/agents/session.py
from uuid import UUID

from chatddx_backend.agents.models import Message, Session
from chatddx_backend.agents.models.session import Identity
from chatddx_backend.agents.schemas import (
    AgentSpec,
    IdentitySpec,
    MessageSpec,
    SessionSpec,
)


async def start_session(
    owner: IdentitySpec,
    agent: AgentSpec,
    description: str | None = None,
) -> SessionSpec:

    session_model = await Session.objects.acreate(
        owner_id=owner.id,
        default_agent_id=agent.id,
        description=description,
    )

    return await resume_session(owner, session_model.uuid)


async def resume_session(
    owner: IdentitySpec,
    uuid: UUID | str,
) -> SessionSpec:

    session_model = (
        await Session.objects.select_related()
        .prefetch_related(
            "messages",
        )
        .aget(
            uuid__startswith=uuid,
            owner_id=owner.id,
        )
    )

    return SessionSpec.model_validate(session_model)


async def refresh_messages(
    session: SessionSpec,
) -> None:
    queryset = Message.objects.select_related().filter(session_id=session.id)

    if len(session.messages) > 0:
        queryset = queryset.filter(pk__gt=session.messages[-1].id)

    session.messages.extend([MessageSpec.model_validate(m) async for m in queryset])


async def get_identity(name: str) -> IdentitySpec:
    instance = await Identity.objects.aget(name=name)
    return IdentitySpec.model_validate(instance)
