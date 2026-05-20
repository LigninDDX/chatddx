# src/chatddx/repo/form_data_in.py
from chatddx.repo.base import BaseFormDataIn
from chatddx.repo.trail_schemas import (
    AgentBase,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)


class ToolFormDataIn(ToolBase, BaseFormDataIn):
    pass


class ConnectionFormDataIn(ConnectionBase, BaseFormDataIn):
    pass


class SamplingParamsFormDataIn(SamplingParamsBase, BaseFormDataIn):
    pass


class OutputTypeFormDataIn(OutputTypeBase, BaseFormDataIn):
    pass


class ToolGroupFormDataIn(ToolGroupBase, BaseFormDataIn):
    tools: list[ToolFormDataIn]


class AgentFormDataIn(AgentBase, BaseFormDataIn):
    connection: ConnectionFormDataIn
    sampling_params: ConnectionFormDataIn
    output_type: ConnectionFormDataIn
    tool_group: ConnectionFormDataIn
