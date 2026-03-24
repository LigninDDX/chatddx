# src/chatddx_backend/agents/specs.py
from decimal import Decimal
from typing import Any

from chatddx_backend.agents.models.enums import (
    CoercionStrategy,
    ProviderType,
    ToolType,
    ValidationStrategy,
)
from chatddx_backend.agents.trail import TrailSpec


class ConnectionSpec(TrailSpec):
    provider: ProviderType
    model: str
    endpoint: str


class SamplingParamsSpec(TrailSpec):
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


class OutputTypeSpec(TrailSpec):
    definition: dict[str, Any]


class ToolSpec(TrailSpec):
    type: ToolType
    description: str | None
    parameters: dict[str, Any] | None


class ToolGroupSpec(TrailSpec):
    instructions: str
    tools: list[ToolSpec] = []


class AgentSpec(TrailSpec):
    instructions: str
    use_tools: bool
    validation_strategy: ValidationStrategy
    coercion_strategy: CoercionStrategy | None

    connection: ConnectionSpec | None = None
    sampling_params: SamplingParamsSpec | None = None
    output_type: OutputTypeSpec | None = None
    tool_group: ToolGroupSpec | None = None
