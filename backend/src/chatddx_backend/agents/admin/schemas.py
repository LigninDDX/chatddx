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
    model_validator,
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
    name: str | None = None
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

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self

    @computed_field
    def parameters_toml(self) -> str:
        return tomli_w.dumps(self.parameters)


class ConnectionFormData(ConnectionSpec):
    name: str | None = None
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

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self

    @computed_field
    def profile_toml(self) -> str:
        return tomli_w.dumps(self.profile)


class SamplingParamsFormData(SamplingParamsSpec):
    name: str | None = None

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

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self

    @computed_field
    def logit_bias_toml(self) -> str:
        return tomli_w.dumps(self.logit_bias)

    @computed_field
    def provider_params_toml(self) -> str:
        return tomli_w.dumps(self.provider_params)


class OutputTypeFormData(OutputTypeSpec):
    name: str | None = None

    toml_input: str | None = Field(default=None, exclude=True)
    definition: Annotated[
        dict[str, JsonValue],
        BeforeValidator(check_toml_input),
    ] = Field(
        exclude=True,
        default_factory=dict,
    )

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self

    @computed_field
    def definition_toml(self) -> str:
        return tomli_w.dumps(self.definition)


class ToolGroupFormData(ToolGroupBase, TrailSpec):
    name: str | None = None
    tools: list[int]

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self


class AgentFormData(AgentSpecRef):
    name: str | None = None

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self


class TemplateData(BaseModel):
    agent: dict[str, AgentFormData]
    connection: dict[str, ConnectionFormData]
    sampling_params: dict[str, SamplingParamsFormData]
    output_type: dict[str, OutputTypeFormData]
    tool_group: dict[str, ToolGroupFormData]
    tool: dict[str, ToolFormData]
