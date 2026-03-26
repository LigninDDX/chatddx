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
    Field,
)

from chatddx_backend.agents.models.enums import (
    CoercionStrategy,
    ProviderType,
    ToolType,
    ValidationStrategy,
)
from chatddx_backend.agents.registry import Registry, RegistryRecord
from chatddx_backend.agents.trail import TrailSchema

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


class ConnectionSchema(TrailSchema, RegistryRecord):
    provider: ProviderType
    model: str
    endpoint: str


class SamplingParamsSchema(TrailSchema, RegistryRecord):
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


class OutputTypeSchema(TrailSchema, RegistryRecord):
    definition: Annotated[
        dict[str, Any],
        AfterValidator(_validate_json_schema),
    ]


class ToolSchema(TrailSchema, RegistryRecord):
    type: ToolType
    description: str | None = None
    parameters: Annotated[
        dict[str, Any] | None,
        AfterValidator(_validate_json_schema),
    ] = None


class ToolGroupSchema(TrailSchema, RegistryRecord):
    instructions: str
    tools: list[ToolSchema]


class AgentSchema(TrailSchema, RegistryRecord):
    instructions: str
    use_tools: bool = False

    validation_strategy: ValidationStrategy = ValidationStrategy.INFORM
    coercion_strategy: CoercionStrategy | None = None

    connection: ConnectionSchema | None = None
    sampling_params: SamplingParamsSchema | None = None
    output_type: OutputTypeSchema | None = None
    tool_group: ToolGroupSchema | None = None
