# src/chatddx_backend/agents/schema.py

from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar

import jsonschema
from ninja import Schema
from pydantic import ConfigDict, Field, field_validator

from chatddx_backend.agents.models.choices import (
    CoercionStrategy,
    ProviderType,
    ToolType,
    ValidationStrategy,
)


def _validate_json_schema(v: Any) -> Any:
    if v is not None:
        try:
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}")
    return v


class TrailInSchema(Schema):
    record_type: ClassVar[str]
    name: str


class TrailOutSchema(Schema):
    id: int
    name: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionIn(TrailInSchema):
    record_type = "connection"

    provider: ProviderType
    model: str
    endpoint: str


class ConnectionOut(TrailOutSchema):
    provider: ProviderType
    model: str
    endpoint: str


class SamplingParamsIn(TrailInSchema):
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


class SamplingParamsOut(TrailOutSchema):
    temperature: Decimal | None = None
    top_p: Decimal | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    seed: int | None = None
    n: int | None = None
    presence_penalty: Decimal | None = None
    frequency_penalty: Decimal | None = None
    stop_sequences: list[str] | None = None
    logit_bias: dict[str, Decimal]
    provider_params: dict[str, Any]


class OutputTypeIn(TrailInSchema):
    record_type = "output_type"

    definition: dict[str, Any]

    _validate_definition = field_validator("definition")(_validate_json_schema)


class OutputTypeOut(TrailOutSchema):
    definition: dict[str, Any]


class ToolIn(TrailInSchema):
    record_type = "tool"

    type: ToolType
    description: str | None = None
    parameters: dict[str, Any] | None = None

    _validate_definition = field_validator("parameters")(_validate_json_schema)


class ToolOut(TrailOutSchema):
    type: ToolType
    description: str | None
    parameters: dict[str, Any] | None


class ToolGroupIn(TrailInSchema):
    record_type = "tool_group"

    instructions: str
    tools: list[ToolIn]


class ToolGroupOut(TrailOutSchema):
    instructions: str
    tools: list[ToolOut] = []


class AgentIn(TrailInSchema):
    record_type = "agent"

    instructions: str
    use_tools: bool = False
    validation_strategy: ValidationStrategy = ValidationStrategy.INFORM
    coercion_strategy: CoercionStrategy | None = None

    connection: ConnectionIn | None = None
    sampling_params: SamplingParamsIn | None = None
    output_type: OutputTypeIn | None = None
    tool_group: ToolGroupIn | None = None


class AgentOut(TrailOutSchema):
    instructions: str
    use_tools: bool
    validation_strategy: ValidationStrategy
    coercion_strategy: CoercionStrategy | None

    connection: ConnectionOut | None = None
    sampling_params: SamplingParamsOut | None = None
    output_type: OutputTypeOut | None = None
    tool_group: ToolGroupOut | None = None
