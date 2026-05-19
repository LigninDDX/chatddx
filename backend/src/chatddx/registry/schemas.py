from pydantic.fields import Field

from chatddx.registry.main import Registry
from chatddx.repo.trail_schemas import (
    AgentSchema,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolSchema,
)


class TrailRegistry(Registry):
    agent: dict[str, AgentSchema] = Field(default_factory=dict)
    connection: dict[str, ConnectionSchema] = Field(default_factory=dict)
    sampling_params: dict[str, SamplingParamsSchema] = Field(default_factory=dict)
    tool_group: dict[str, ToolGroupSchema] = Field(default_factory=dict)
    tool: dict[str, ToolSchema] = Field(default_factory=dict)
    output_type: dict[str, OutputTypeSchema] = Field(default_factory=dict)
