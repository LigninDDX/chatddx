# src/chatddx_backend/agents/schemas.py
from __future__ import annotations

from decimal import Decimal
from typing import (
    Annotated,
    Any,
    TypeVar,
)

import jsonschema
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
)

from chatddx_backend.agents.models.enums import (
    CoercionStrategy,
    ProviderType,
    ToolType,
    ValidationStrategy,
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


class ConnectionBase(BaseModel):
    provider: ProviderType
    model: str
    endpoint: str


class ConnectionSchema(ConnectionBase, TrailSchema, RegistryRecord):
    pass


class ConnectionSpec(ConnectionBase, TrailSpec):
    pass


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
    type: ToolType
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
    validation_strategy: ValidationStrategy = ValidationStrategy.INFORM
    coercion_strategy: CoercionStrategy | None = None


class AgentSchema(AgentBase, TrailSchema, RegistryRecord):
    connection: ConnectionSchema | None = None
    sampling_params: SamplingParamsSchema | None = None
    output_type: OutputTypeSchema | None = None
    tool_group: ToolGroupSchema | None = None


class AgentSpec(AgentBase, TrailSpec):
    connection: ConnectionSpec | None = None
    sampling_params: SamplingParamsSpec | None = None
    output_type: OutputTypeSpec | None = None
    tool_group: ToolGroupSpec | None = None
