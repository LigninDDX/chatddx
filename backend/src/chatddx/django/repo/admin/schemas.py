# src/chatddx/django/repo/admin/schemas.py
from __future__ import annotations

import tomllib
from typing import Annotated, Any, cast

import tomli_w
from django.db.models import Model as DjangoModel
from ninja import Schema as NinjaSchema
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    JsonValue,
    PlainSerializer,
    ValidationInfo,
    field_validator,
    model_validator,
)

from chatddx.django.repo.models import ToolModel
from chatddx.django.repo.schemas import (
    AgentBase,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)


def extract_django_pk(value: Any):
    if isinstance(value, DjangoModel):
        return value.pk
    return value


def parse_toml_or_dict(v: Any) -> Any:
    match v:
        case None:
            return None
        case str():
            if not v.strip():
                return None
            try:
                return tomllib.loads(v)
            except Exception as e:
                raise ValueError(e)
        case dict():
            return v  # pyright: ignore[reportUnknownVariableType]
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
            return v  # pyright: ignore[reportUnknownVariableType]
        case _:
            raise ValueError(f"Unexpected input: {v}")


def dict_to_toml(v: dict[str, Any] | None) -> str:
    return tomli_w.dumps(v).strip() if v is not None else ""


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
    def add_name_from_context(self, info: ValidationInfo):
        if info.context:
            self.name = info.context.get("name")
        return self


class BaseFormData:
    pass


class ToolFormData(ToolBase, BranchFormData, BaseFormData):
    # TODO: Actual confusion here, when do we allow None and when don't we?
    parameters: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class ConnectionFormData(ConnectionBase, BranchFormData, BaseFormData):
    profile: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class SamplingParamsFormData(SamplingParamsBase, BranchFormData, BaseFormData):
    logit_bias: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]
    provider_params: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]
    stop_sequences: TextList | None = Field(default_factory=list)


class OutputTypeFormData(OutputTypeBase, BranchFormData, BaseFormData):
    definition: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class ToolGroupFormData(ToolGroupBase, BranchFormData, BaseFormData):
    tools: list[int]

    @field_validator(
        "tools",
        mode="before",
    )
    @classmethod
    def extract_django_pks(cls, values: list[Any]):
        return [extract_django_pk(value) for value in values]


class AgentFormData(AgentBase, BranchFormData, BaseFormData):
    connection_id: int
    sampling_params_id: int
    output_type_id: int
    tool_group_id: int

    @field_validator(
        "connection_id",
        "sampling_params_id",
        "output_type_id",
        "tool_group_id",
        mode="before",
    )
    @classmethod
    def extract_django_pk(cls, value: Any):
        return extract_django_pk(value)


class TemplateData(BaseModel):
    agent: dict[str, AgentFormData]
    connection: dict[str, ConnectionFormData]
    sampling_params: dict[str, SamplingParamsFormData]
    output_type: dict[str, OutputTypeFormData]
    tool_group: dict[str, ToolGroupFormData]
    tool: dict[str, ToolFormData]
