# src/chatddx_backend/agents/admin/schemas.py
from __future__ import annotations

from typing import Annotated, Any, cast

import tomli
import tomli_w
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    JsonValue,
    ValidationInfo,
    computed_field,
)

from chatddx_backend.agents.models import ToolModel
from chatddx_backend.agents.schemas import (
    AgentSpecRef,
    ConnectionSpec,
    OutputTypeSpec,
    SamplingDecimal,
    SamplingParamsSpec,
    ToolGroupBase,
    ToolSpec,
)
from chatddx_backend.agents.trail import TrailSpec


def check_toml_input(v: Any, info: ValidationInfo) -> dict[str, Any]:
    toml_input = info.data.get(f"{info.field_name}_toml_input")

    if toml_input:
        try:
            return tomli.loads(toml_input)
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML format in {info.field_name}: {e}")

    return v or {}


def resolve_tools(v: Any) -> list[ToolFormData]:
    if isinstance(v, list):
        v = cast(list[Any], v)

        if all(isinstance(x, ToolFormData) for x in v):
            return cast(list[ToolFormData], v)

        if all(isinstance(x, int) for x in v):
            return [
                ToolFormData.model_validate(tool_model)
                for tool_model in ToolModel.objects.filter(pk__in=v)
            ]

    raise ValueError(f"unexpected value {v}")


class ToolFormData(ToolSpec):
    make_template: bool = False
    parameters_toml_input: str | None = Field(
        default=None,
        exclude=True,
    )
    parameters: Annotated[
        dict[str, JsonValue],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    @computed_field
    def parameters_toml(self) -> str:
        return tomli_w.dumps(self.parameters)


class ConnectionFormData(ConnectionSpec):
    make_template: bool = False
    profile_toml_input: str | None = Field(
        default=None,
        exclude=True,
    )
    profile: Annotated[
        dict[str, JsonValue],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    @computed_field
    def profile_toml(self) -> str:
        return tomli_w.dumps(self.profile)


class SamplingParamsFormData(SamplingParamsSpec):
    make_template: bool = False

    logit_bias_toml_input: str | None = Field(default=None, exclude=True)
    logit_bias: Annotated[
        dict[str, SamplingDecimal],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    provider_params_toml_input: str | None = Field(default=None, exclude=True)
    provider_params: Annotated[
        dict[str, JsonValue],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    @computed_field
    def logit_bias_toml(self) -> str:
        return tomli_w.dumps(self.logit_bias)

    @computed_field
    def provider_params_toml(self) -> str:
        return tomli_w.dumps(self.provider_params)


class OutputTypeFormData(OutputTypeSpec):
    make_template: bool = False

    toml_input: str | None = Field(default=None, exclude=True)
    definition: Annotated[
        dict[str, JsonValue],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    @computed_field
    def definition_toml(self) -> str:
        return tomli_w.dumps(self.definition)


class ToolGroupFormData(ToolGroupBase, TrailSpec):
    make_template: bool = False
    tools: list[int]


class AgentFormData(AgentSpecRef):
    make_template: bool = False


class TemplateData(BaseModel):
    agent: dict[int, AgentFormData]
    connection: dict[int, ConnectionFormData]
    sampling_params: dict[int, SamplingParamsFormData]
    output_type: dict[int, OutputTypeFormData]
    tool_group: dict[int, ToolGroupFormData]
