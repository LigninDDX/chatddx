# src/chatddx/django/repo/schemas.py
from __future__ import annotations

import tomllib
from decimal import ROUND_HALF_UP, Decimal
from typing import (
    Annotated,
    Any,
)

import jsonschema
import tomli_w
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    GetCoreSchemaHandler,
    HttpUrl,
    JsonValue,
)
from pydantic_core import core_schema

from chatddx.core.choices import (
    CoercionChoices,
    ProviderChoices,
    ToolChoices,
    ValidationChoices,
)
from chatddx.registry.main import RegistryRecord
from chatddx.repo.base import TrailSchema

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


class ConnectionBase(BaseModel):
    provider: ProviderChoices
    model: str
    endpoint: HttpUrl
    profile: dict[str, JsonValue] = Field(default_factory=dict)


class ConnectionSchema(ConnectionBase, TrailSchema, RegistryRecord):
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


class OutputTypeBase(BaseModel):
    definition: Annotated[
        dict[str, JsonValue],
        AfterValidator(_validate_json_schema),
    ] = Field(default_factory=dict)
    validation_strategy: ValidationChoices = ValidationChoices.INFORM
    coercion_strategy: CoercionChoices = CoercionChoices.NATIVE


class OutputTypeSchema(OutputTypeBase, TrailSchema, RegistryRecord):
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


class ToolGroupBase(BaseModel):
    instructions: str


class ToolGroupSchema(ToolGroupBase, TrailSchema, RegistryRecord):
    tools: list[ToolSchema]


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
