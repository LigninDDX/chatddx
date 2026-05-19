# src/chatddx/django/repo/schemas.py
from pydantic import (
    BaseModel,
)

from chatddx.repo.base import TrailSpec
from chatddx.repo.trail_schemas import (
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)


class ConnectionSpec(ConnectionBase, TrailSpec):
    pass


class SamplingParamsSpec(SamplingParamsBase, TrailSpec):
    pass


class OutputTypeSpec(OutputTypeBase, TrailSpec):
    pass


class ToolSpec(ToolBase, TrailSpec):
    pass


class ToolGroupSpec(ToolGroupBase, TrailSpec):
    tools: list[ToolSpec]


class AgentBase(BaseModel):
    instructions: str


class AgentSpec(AgentBase, TrailSpec):
    connection: ConnectionSpec
    sampling_params: SamplingParamsSpec
    output_type: OutputTypeSpec
    tool_group: ToolGroupSpec
