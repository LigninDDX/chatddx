# src/chatddx_backend/agents/admin/schemas.py
from __future__ import annotations

import tomllib
from typing import Annotated, Any, cast

import tomli_w
from ninja import Schema as NinjaSchema
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    JsonValue,
    PlainSerializer,
    model_validator,
)

from chatddx_backend.agents.models import ToolModel
from chatddx_backend.agents.schemas import (
    AgentBase,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)


def parse_toml_or_dict(v: Any) -> dict | None:
    match v:
        case None:
            return None
        case str():
            if not v.strip():
                return None
            try:
                return tomllib.loads(v)
            except Exception as e:
                raise ValueError(f"Invalid TOML: {e}. Got: '{v}'.")
        case dict():
            return v
        case _:
            raise ValueError(f"Unexpected input: {v}")


def parse_text_or_list(v: Any) -> list[str] | None:
    match v:
        case None:
            return None
        case str():
            if not v.strip():
                return None
            return [line.strip() for line in v.splitlines() if line.strip()]
        case list():
            return v
        case _:
            raise ValueError(f"Unexpected input: {v}")


def dict_to_toml(v: dict | None) -> str:
    return tomli_w.dumps(v) if v is not None else ""


def list_to_text(v: list[str] | None) -> str:
    return "\n".join(v) if v is not None else ""


TomlDict = Annotated[
    dict[str, JsonValue] | None,
    BeforeValidator(parse_toml_or_dict),
    PlainSerializer(
        dict_to_toml,
        return_type=str,
        when_used="json",
    ),
]


TextList = Annotated[
    list[str] | None,
    BeforeValidator(parse_text_or_list),
    PlainSerializer(
        list_to_text,
        return_type=str,
        when_used="json",
    ),
]


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


class BranchFormData(NinjaSchema):
    id: int | None = None
    name: str | None = None

    @model_validator(mode="after")
    def add_name_from_context(self, info):
        if info.context:
            self.name = info.context.get("name")
        return self


class ToolFormData(ToolBase, BranchFormData):
    parameters: TomlDict = Field(default_factory=dict)


class ConnectionFormData(ConnectionBase, BranchFormData):
    profile: TomlDict = Field(default_factory=dict)


class SamplingParamsFormData(SamplingParamsBase, BranchFormData):
    logit_bias: TomlDict = Field(default_factory=dict)
    provider_params: TomlDict = Field(default_factory=dict)
    stop_sequences: TextList | None = Field(default_factory=list)


class OutputTypeFormData(OutputTypeBase, BranchFormData):
    definition: TomlDict = Field(default_factory=dict)


class ToolGroupFormData(ToolGroupBase, BranchFormData):
    tools: list[int]


class AgentFormData(AgentBase, BranchFormData):
    connection_id: int
    sampling_params_id: int
    output_type_id: int
    tool_group_id: int


class TemplateData(BaseModel):
    agent: dict[str, AgentFormData]
    connection: dict[str, ConnectionFormData]
    sampling_params: dict[str, SamplingParamsFormData]
    output_type: dict[str, OutputTypeFormData]
    tool_group: dict[str, ToolGroupFormData]
    tool: dict[str, ToolFormData]
