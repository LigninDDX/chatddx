# src/chatddx_backend/agents/schemas.py
from __future__ import annotations

import tomllib
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import (
    Annotated,
    Any,
    Generic,
    TypeVar,
)
from uuid import UUID

import jsonschema
import tomli_w
from ninja import Schema as NinjaSchema
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    GetCoreSchemaHandler,
    HttpUrl,
    JsonValue,
)
from pydantic_ai import ModelMessage
from pydantic_core import core_schema
from repo.models.choices import (
    CoercionChoices,
    MessageKindChoices,
    ProviderChoices,
    RoleChoices,
    ToolChoices,
    ValidationChoices,
)

from chatddx.django.repo.registry import Registry, RegistryRecord
from chatddx.django.repo.trail import TrailSchema, TrailSpec

PRECISION = Decimal("0.01")


class SamplingDecimal(Decimal):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, v: Any) -> "SamplingDecimal":
        return cls(Decimal(str(v)).quantize(PRECISION, rounding=ROUND_HALF_UP))


def _validate_json_schema(v: Any) -> Any:
    if v is not None:
        try:
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}")
        check_v = tomllib.loads(tomli_w.dumps(v))
        assert check_v == v
    return v


class TrailRegistry(Registry):
    agent: dict[str, AgentSchema] = Field(default_factory=dict)
    connection: dict[str, ConnectionSchema] = Field(default_factory=dict)
    sampling_params: dict[str, SamplingParamsSchema] = Field(default_factory=dict)
    tool_group: dict[str, ToolGroupSchema] = Field(default_factory=dict)
    tool: dict[str, ToolSchema] = Field(default_factory=dict)
    output_type: dict[str, OutputTypeSchema] = Field(default_factory=dict)


class IdentityBase(BaseModel):
    name: str
    user_id: int | None = None
    guest_id: UUID | None = None
    secrets: dict[str, JsonValue] = Field(default_factory=dict)


class IdentitySchema(IdentityBase):
    pass


class IdentitySpec(IdentityBase, NinjaSchema):
    id: int


class BranchBase(BaseModel):
    owner_id: int
    name: str
    timestamp: datetime | None = None


SchemaT = TypeVar("SchemaT", bound=TrailSchema)


class BranchSchema(BranchBase, Generic[SchemaT]):
    target_type: type[SchemaT]
    target_id: int


SpecT = TypeVar("SpecT", bound=TrailSpec)


class BranchSpec(BranchBase, NinjaSchema, Generic[SpecT]):
    id: int
    target: SpecT


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


class ConnectionBase(BaseModel):
    provider: ProviderChoices
    model: str
    endpoint: HttpUrl
    profile: dict[str, JsonValue] = Field(default_factory=dict)


class ConnectionSchema(ConnectionBase, TrailSchema, RegistryRecord):
    pass


class ConnectionSpec(ConnectionBase, TrailSpec):
    pass


class SamplingParamsBase(BaseModel):
    temperature: SamplingDecimal | None = None
    top_p: SamplingDecimal | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    seed: int | None = None
    n: int | None = None
    presence_penalty: SamplingDecimal | None = None
    frequency_penalty: SamplingDecimal | None = None
    stop_sequences: list[str] | None = None
    logit_bias: dict[str, SamplingDecimal] = Field(default_factory=dict)
    provider_params: dict[str, JsonValue] = Field(default_factory=dict)


class SamplingParamsSchema(SamplingParamsBase, TrailSchema, RegistryRecord):
    pass


class SamplingParamsSpec(SamplingParamsBase, TrailSpec):
    pass


class OutputTypeBase(BaseModel):
    definition: Annotated[
        dict[str, JsonValue],
        AfterValidator(_validate_json_schema),
    ] = Field(default_factory=dict)
    validation_strategy: ValidationChoices = ValidationChoices.INFORM
    coercion_strategy: CoercionChoices = CoercionChoices.NATIVE


class OutputTypeSchema(OutputTypeBase, TrailSchema, RegistryRecord):
    pass


class OutputTypeSpec(OutputTypeBase, TrailSpec):
    pass


class ToolBase(BaseModel):
    command: str
    type: ToolChoices
    description: str = ""
    parameters: Annotated[
        dict[str, JsonValue],
        AfterValidator(_validate_json_schema),
    ] = Field(default_factory=dict)


class ToolSchema(ToolBase, TrailSchema, RegistryRecord):
    pass


class ToolSpec(ToolBase, TrailSpec):
    pass


class ToolGroupBase(BaseModel):
    instructions: str


class ToolGroupSchema(ToolGroupBase, TrailSchema, RegistryRecord):
    tools: list[ToolSchema]


class ToolGroupSchemaRef(ToolGroupBase, TrailSchema, RegistryRecord):
    tools: list[int]


class ToolGroupSpec(ToolGroupBase, TrailSpec):
    tools: list[ToolSpec]


class AgentBase(BaseModel):
    instructions: str


class AgentSchema(AgentBase, TrailSchema, RegistryRecord):
    connection: ConnectionSchema
    sampling_params: SamplingParamsSchema = Field(
        default_factory=SamplingParamsSchema,
    )
    output_type: OutputTypeSchema = Field(
        default_factory=lambda: OutputTypeSchema(
            definition={},
        ),
    )
    tool_group: ToolGroupSchema = Field(
        default_factory=lambda: ToolGroupSchema(
            instructions="",
            tools=[],
        ),
    )


class AgentSchemaRef(AgentBase, TrailSchema, RegistryRecord):
    connection_id: int
    sampling_params_id: int
    output_type_id: int
    tool_group_id: int


class AgentSpec(AgentBase, TrailSpec):
    connection: ConnectionSpec
    sampling_params: SamplingParamsSpec
    output_type: OutputTypeSpec
    tool_group: ToolGroupSpec
