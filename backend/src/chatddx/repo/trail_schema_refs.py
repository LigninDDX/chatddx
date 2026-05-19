from chatddx.registry.main import RegistryRecord
from chatddx.repo.base import TrailSchemaRef
from chatddx.repo.trail_schemas import (
    AgentBase,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
)


class ToolGroupSchemaRef(ToolGroupBase, TrailSchemaRef, RegistryRecord):
    tools: list[int]


class AgentSchemaRef(AgentBase, TrailSchemaRef, RegistryRecord):
    connection_id: int
    sampling_params_id: int
    output_type_id: int
    tool_group_id: int


class ConnectionSchemaRef(ConnectionBase, TrailSchemaRef, RegistryRecord):
    pass


class SamplingParamsSchemaRef(SamplingParamsBase, TrailSchemaRef, RegistryRecord):
    pass


class OutputTypeSchemaRef(OutputTypeBase, TrailSchemaRef, RegistryRecord):
    pass


class ToolSchemaRef(ToolBase, TrailSchemaRef, RegistryRecord):
    pass
