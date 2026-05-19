from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ninja import Schema as NinjaSchema
from pydantic import BaseModel, Field, JsonValue
from pydantic_ai import ModelMessage

from chatddx.core.choices import MessageKindChoices, RoleChoices
from chatddx.repo.base import BranchSchema, BranchSpec
from chatddx.repo.trail_schemas import AgentSchema
from chatddx.repo.trail_specs import AgentSpec


class IdentityBase(BaseModel):
    name: str
    user_id: int | None = None
    guest_id: UUID | None = None
    secrets: dict[str, JsonValue] = Field(default_factory=dict)


class IdentitySchema(IdentityBase):
    pass


class IdentitySpec(IdentityBase, NinjaSchema):
    id: int


class SessionBase(BaseModel):
    uuid: UUID
    description: str | None
    timestamp: datetime
    owner_id: int


class SessionSchema(SessionBase):
    default_agent: BranchSchema[AgentSchema]


class SessionSpec(SessionBase, NinjaSchema):
    id: int
    default_agent: BranchSpec[AgentSpec]
    messages: list[MessageSpec]


class MessageSpec(NinjaSchema):
    id: int
    agent_id: int
    session_id: int
    role: RoleChoices
    run_id: UUID
    kind: MessageKindChoices
    payload: ModelMessage
    timestamp: datetime
