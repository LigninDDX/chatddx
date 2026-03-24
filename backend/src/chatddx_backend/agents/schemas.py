# src/chatddx_backend/agents/schemas.py

from decimal import Decimal
from typing import Any

import jsonschema
from pydantic import Field, field_validator

from chatddx_backend.agents.models.enums import (
    CoercionStrategy,
    ProviderType,
    ToolType,
    ValidationStrategy,
)
from chatddx_backend.agents.trail import TrailSchema


def _validate_json_schema(v: Any) -> Any:
    if v is not None:
        try:
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}")
    return v


class ConnectionSchema(TrailSchema):
    record_type = "connection"

    provider: ProviderType
    model: str
    endpoint: str


class SamplingParamsSchema(TrailSchema):
    record_type = "sampling_params"

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


class OutputTypeSchema(TrailSchema):
    record_type = "output_type"

    definition: dict[str, Any]

    _validate_definition = field_validator("definition")(_validate_json_schema)


class ToolSchema(TrailSchema):
    record_type = "tool"

    type: ToolType
    description: str | None = None
    parameters: dict[str, Any] | None = None

    _validate_definition = field_validator("parameters")(_validate_json_schema)


class ToolGroupSchema(TrailSchema):
    record_type = "tool_group"

    instructions: str
    tools: list[ToolSchema]


class AgentSchema(TrailSchema):
    record_type = "agent"

    instructions: str
    use_tools: bool = False
    validation_strategy: ValidationStrategy = ValidationStrategy.INFORM
    coercion_strategy: CoercionStrategy | None = None

    connection: ConnectionSchema | None = None
    sampling_params: SamplingParamsSchema | None = None
    output_type: OutputTypeSchema | None = None
    tool_group: ToolGroupSchema | None = None
