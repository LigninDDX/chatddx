# src/chatddx/repo/form_data_out.py
from typing import Annotated

from pydantic import BeforeValidator, Field

from chatddx.core.fields import dict_to_toml, list_to_text
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
    tools: list[int]


class SubAgentFormDataOut(AgentBase, BaseFormDataOut):
    pass


class AgentFormDataOut(AgentBase, BaseFormDataOut):
    connection_id: int = Field(serialization_alias="connection")
    sampling_params_id: int = Field(serialization_alias="sampling_params")
    output_type_id: int = Field(serialization_alias="output_type")
    tool_group_id: int = Field(serialization_alias="tool_group")


class SuperAgentFormDataOut(AgentBase, BaseFormDataOut):
    connection: ConnectionFormDataOut
    sampling_params: SamplingParamsFormDataOut
    output_type: OutputTypeFormDataOut
    tool_group: ToolGroupFormDataOut
