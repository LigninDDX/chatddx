# src/chatddx/repo/form_data.py
from __future__ import annotations

from typing import Any

from pydantic import (
    Field,
    field_validator,
)

from chatddx.core.fields import TextList, TomlDict
from chatddx.repo.base import BaseFormData
from chatddx.repo.trail_schemas import (
    AgentBase,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)
from chatddx.utils import extract_django_pk


class ToolFormData(ToolBase, BaseFormData):
    # TODO: Actual confusion here, when do we allow None and when don't we?
    parameters: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class ConnectionFormData(ConnectionBase, BaseFormData):
    profile: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class SamplingParamsFormData(SamplingParamsBase, BaseFormData):
    logit_bias: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]
    provider_params: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]
    stop_sequences: TextList | None = Field(default_factory=list)


class OutputTypeFormData(OutputTypeBase, BaseFormData):
    definition: TomlDict = Field(default_factory=dict)  # pyright: ignore[reportIncompatibleVariableOverride]


class ToolGroupFormData(ToolGroupBase, BaseFormData):
    tools: list[int]

    @field_validator(
        "tools",
        mode="before",
    )
    @classmethod
    def extract_django_pks(cls, values: list[Any]):
        pks = [extract_django_pk(value) for value in values]
        return pks


class AgentFormData(AgentBase, BaseFormData):
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
