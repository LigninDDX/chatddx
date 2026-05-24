# src/chatddx/repo/form_data_out.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from chatddx.core.fields import CoercedStr, dict_to_toml, list_to_text
from chatddx.repo.base import BaseFormDataOut
from chatddx.repo.trail_schemas import (
    AgentBase,
    ConnectionBasePrimitives,
    OutputTypeBasePrimitives,
    SamplingParamsBasePrimitives,
    ToolBasePrimitives,
    ToolGroupBase,
)

TomlString = Annotated[str, BeforeValidator(dict_to_toml)]
TextList = Annotated[str, BeforeValidator(list_to_text)]


@dataclass
class TemplateMeta:
    name: str
    selector: str
    fields: list[str]


def TemplateField(
    name: str,
    selector: str | None = None,
    prefix: str = "",
):
    prefixed_name = f"{prefix}_{name}"
    if selector is None:
        selector = name

    fields = {
        "agent": AgentFormDataOut,
        "connection": ConnectionFormDataOut,
        "sampling_params": SamplingParamsFormDataOut,
        "output_type": OutputTypeFormDataOut,
        "tool_group": ToolGroupFormDataOut,
    }[name].model_fields

    json_schema_extra = TemplateMeta(
        name=name,
        selector=selector,
        fields=list(fields),
    )
    return Field(
        json_schema_extra=asdict(json_schema_extra),
        serialization_alias=name,
    )


class TemplateData(BaseModel):
    agent: dict[str, AgentFormDataOut]
    connection: dict[str, ConnectionFormDataOut]
    sampling_params: dict[str, SamplingParamsFormDataOut]
    output_type: dict[str, OutputTypeFormDataOut]
    tool_group: dict[str, ToolGroupFormDataOut]
    tool: dict[str, ToolFormDataOut]


class ToolFormDataOut(ToolBasePrimitives, BaseFormDataOut):
    parameters: TomlString


class ConnectionFormDataOut(ConnectionBasePrimitives, BaseFormDataOut):
    profile: TomlString


class SamplingParamsFormDataOut(SamplingParamsBasePrimitives, BaseFormDataOut):
    logit_bias: TomlString
    provider_params: TomlString
    stop_sequences: TextList


class OutputTypeFormDataOut(OutputTypeBasePrimitives, BaseFormDataOut):
    definition: TomlString


class ToolGroupFormDataOut(ToolGroupBase, BaseFormDataOut):
    tools: list[CoercedStr]


class AgentFormDataOut(AgentBase, BaseFormDataOut):
    id: CoercedStr = Field(serialization_alias="template")
    connection_id: CoercedStr = Field(serialization_alias="connection")
    sampling_params_id: CoercedStr = Field(serialization_alias="sampling_params")
    output_type_id: CoercedStr = Field(serialization_alias="output_type")
    tool_group_id: CoercedStr = Field(serialization_alias="tool_group")


class SuperAgentFormDataOut(AgentBase, BaseFormDataOut):
    connection: ConnectionFormDataOut
    sampling_params: SamplingParamsFormDataOut
    output_type: OutputTypeFormDataOut
    tool_group: ToolGroupFormDataOut
