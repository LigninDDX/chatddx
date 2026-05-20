from chatddx.registry.main import RegistryRecord
from chatddx.repo.base import TrailSchemaRef
from chatddx.repo.trail_schemas import (
    AgentBase,
    AgentSchema,
    ConnectionBase,
    OutputTypeBase,
    SamplingParamsBase,
    ToolBase,
    ToolGroupBase,
    ToolGroupSchema,
)


class ToolGroupSchemaRef(
    TrailSchemaRef,
    ToolGroupBase,
    RegistryRecord,
):
    tools: list[int]

    @classmethod
    def from_schema(cls, schema: ToolGroupSchema):
        from chatddx.repo.loaders.model_loader import create_trail

        tool_ids = [create_trail(tool).pk for tool in schema.tools]
        return cls.model_validate(
            schema.model_dump(exclude={"tools"}) | {"tools": tool_ids}
        )


class AgentSchemaRef(
    TrailSchemaRef,
    AgentBase,
    RegistryRecord,
):
    connection_id: int
    sampling_params_id: int
    output_type_id: int
    tool_group_id: int

    @classmethod
    def from_schema(cls, schema: AgentSchema):
        from chatddx.repo.loaders.model_loader import create_trail

        relations = ["connection", "sampling_params", "output_type", "tool_group"]
        ref_ids = {
            ref + "_id": create_trail(getattr(schema, ref)).pk for ref in relations
        }
        return cls.model_validate(schema.model_dump(exclude=set(relations)) | ref_ids)


class ConnectionSchemaRef(
    TrailSchemaRef,
    ConnectionBase,
    RegistryRecord,
):
    pass


class SamplingParamsSchemaRef(
    TrailSchemaRef,
    SamplingParamsBase,
    RegistryRecord,
):
    pass


class OutputTypeSchemaRef(
    TrailSchemaRef,
    OutputTypeBase,
    RegistryRecord,
):
    pass


class ToolSchemaRef(
    TrailSchemaRef,
    ToolBase,
    RegistryRecord,
):
    pass
