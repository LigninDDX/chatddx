# src/chatddx_backend/agents/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import (
    Annotated,
    Any,
    TypeVar,
)
from uuid import UUID

import jsonschema
from ninja import Schema as NinjaSchema
from pydantic import (
    AfterValidator,
    AliasChoices,
    AliasPath,
    BaseModel,
    Field,
)
from pydantic_ai import ModelMessage

from chatddx_backend.agents.models.choices import (
    CoercionChoices,
    ProviderChoices,
    RoleChoices,
    ToolChoices,
    ValidationChoices,
)
from chatddx_backend.agents.registry import Registry, RegistryRecord
from chatddx_backend.agents.trail import TrailSchema, TrailSpec

TrailSchemaT = TypeVar("TrailSchemaT", bound=TrailSchema)


def _validate_json_schema(v: Any) -> Any:
    if v is not None:
        try:
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}")
    return v


class TrailRegistry(Registry):
    agent: dict[str, AgentSchema] = {}
    connection: dict[str, ConnectionSchema] = {}
    sampling_params: dict[str, SamplingParamsSchema] = {}
    tool_group: dict[str, ToolGroupSchema] = {}
    tool: dict[str, ToolSchema] = {}
    output_type: dict[str, OutputTypeSchema] = {}


class UserBase(BaseModel):
    pass


class UserSchema(UserBase):
    pass


class UserSpec(UserBase, NinjaSchema):
    id: int = Field(
        validation_alias=AliasChoices(
            "id",
            AliasPath("auth_user", "id"),
        ),
    )
    name: str = Field(
        validation_alias=AliasChoices(
            "name",
            AliasPath("auth_user", "username"),
        )
    )
    default_agent: AgentSpec


class SessionBase(BaseModel):
    uuid: UUID
    description: str | None
    created_at: datetime


class SessionSchema(SessionBase):
    user: UserSchema
    default_agent: AgentSchema


class SessionSpec(SessionBase, NinjaSchema):
    id: int
    user: UserSpec
    default_agent: AgentSpec
    messages: list[MessageSpec]


class MessageSpec(NinjaSchema):
    id: int
    agent_id: int
    role: RoleChoices
    run_id: UUID
    payload: ModelMessage
    timestamp: datetime


class ConnectionBase(BaseModel):
    provider: ProviderChoices
    model: str
    endpoint: str


class ConnectionSchema(ConnectionBase, TrailSchema, RegistryRecord):
    profile: dict[str, Any] = Field(default_factory=dict)


class ConnectionSpec(ConnectionBase, TrailSpec):
    profile: dict[str, Any] = Field(default_factory=dict)


class SamplingParamsBase(BaseModel):
    temperature: Decimal | None = None
    top_p: Decimal | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    seed: int | None = None
    n: int | None = None
    presence_penalty: Decimal | None = None
    frequency_penalty: Decimal | None = None
    stop_sequences: list[str] | None = None
    logit_bias: dict[str, Decimal] = Field(default_factory=dict)
    provider_params: dict[str, Any] = Field(default_factory=dict)


class SamplingParamsSchema(SamplingParamsBase, TrailSchema, RegistryRecord):
    pass


class SamplingParamsSpec(SamplingParamsBase, TrailSpec):
    pass


class OutputTypeBase(BaseModel):
    definition: Annotated[
        dict[str, Any],
        AfterValidator(_validate_json_schema),
    ]


class OutputTypeSchema(OutputTypeBase, TrailSchema, RegistryRecord):
    pass


class OutputTypeSpec(OutputTypeBase, TrailSpec):
    pass


class ToolBase(BaseModel):
    type: ToolChoices
    description: str | None = None
    parameters: Annotated[
        dict[str, Any] | None,
        AfterValidator(_validate_json_schema),
    ] = None


class ToolSchema(ToolBase, TrailSchema, RegistryRecord):
    pass


class ToolSpec(ToolBase, TrailSpec):
    pass


class ToolGroupBase(BaseModel):
    instructions: str


class ToolGroupSchema(ToolGroupBase, TrailSchema, RegistryRecord):
    tools: list[ToolSchema]


class ToolGroupSpec(ToolGroupBase, TrailSpec):
    tools: list[ToolSpec] = []


class AgentBase(BaseModel):
    instructions: str
    validation_strategy: ValidationChoices = ValidationChoices.INFORM
    coercion_strategy: CoercionChoices = CoercionChoices.NATIVE


class AgentSchema(AgentBase, TrailSchema, RegistryRecord):
    connection: ConnectionSchema
    sampling_params: SamplingParamsSchema = SamplingParamsSchema(
        name="default",
    )
    output_type: OutputTypeSchema = OutputTypeSchema(
        name="default",
        definition={},
    )
    tool_group: ToolGroupSchema = ToolGroupSchema(
        name="default",
        instructions="",
        tools=[],
    )


class AgentSpec(AgentBase, TrailSpec):
    connection: ConnectionSpec
    sampling_params: SamplingParamsSpec
    output_type: OutputTypeSpec
    tool_group: ToolGroupSpec
