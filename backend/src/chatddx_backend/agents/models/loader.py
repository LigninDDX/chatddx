# src/chatddx_backend/agents/models/loader.py
from django.db import IntegrityError

from chatddx_backend.agents.admin.schemas import (
    AgentFormData,
    ConnectionFormData,
    OutputTypeFormData,
    SamplingParamsFormData,
    ToolFormData,
    ToolGroupFormData,
)
from chatddx_backend.agents.models import (
    AgentModel,
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
    ToolModel,
)
from chatddx_backend.agents.models.history import (
    AgentBranchModel,
    ConnectionBranchModel,
    OutputTypeBranchModel,
    SamplingParamsBranchModel,
    ToolBranchModel,
    ToolGroupBranchModel,
)
from chatddx_backend.agents.schemas import (
    AgentSchema,
    AgentSchemaRef,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolGroupSchemaRef,
    ToolSchema,
)
from chatddx_backend.agents.trail import TrailSchema

model_map = {
    AgentSchema: (
        AgentModel,
        AgentBranchModel,
        AgentFormData,
    ),
    ConnectionSchema: (
        ConnectionModel,
        ConnectionBranchModel,
        ConnectionFormData,
    ),
    SamplingParamsSchema: (
        SamplingParamsModel,
        SamplingParamsBranchModel,
        SamplingParamsFormData,
    ),
    ToolSchema: (
        ToolModel,
        ToolBranchModel,
        ToolFormData,
    ),
    OutputTypeSchema: (
        OutputTypeModel,
        OutputTypeBranchModel,
        OutputTypeFormData,
    ),
    ToolGroupSchema: (
        ToolGroupModel,
        ToolGroupBranchModel,
        ToolGroupFormData,
    ),
}


def _ref_tool_group(schema):
    tool_ids = [create_trail(tool).pk for tool in schema.tools]
    return ToolGroupSchemaRef(**(schema.model_dump() | {"tools": tool_ids}))


def _ref_agent(schema):
    refs = ["connection", "sampling_params", "output_type", "tool_group"]
    ref_ids = {ref + "_id": create_trail(getattr(schema, ref)).pk for ref in refs}
    return AgentSchemaRef(**schema.model_dump(exclude=set(refs)) | ref_ids)


def create_trail(schema):
    TrailModel, _, _ = model_map[type(schema)]
    match schema:
        case AgentSchema():
            schema = _ref_agent(schema)
        case ToolGroupSchema():
            schema = _ref_tool_group(schema)
        case _:
            pass
    try:
        trail_instance, _ = TrailModel.objects.get_or_create(
            fingerprint=schema.fingerprint,
            **schema.model_dump(exclude={"fingerprint"}),
        )
    except IntegrityError:
        trail_instance = TrailModel.objects.get(fingerprint=schema.fingerprint)

    return trail_instance


def create_branch(
    schema: TrailSchema,
    name: str,
    owner_id: int,
):
    _, BranchModel, _ = model_map[type(schema)]
    trail_instance = create_trail(schema)
    branch_instance = BranchModel.objects.create(
        name=name,
        owner_id=owner_id,
        target=trail_instance,
    )
    return branch_instance


def create_form_data(
    schema: TrailSchema,
    name: str,
    owner_id: int,
    key: str = "id",
):
    _, _, FormData = model_map[type(schema)]
    branch = create_branch(
        schema,
        name,
        owner_id,
    )
    keys = {
        "id": branch.pk,
        "name": name,
    }
    return keys[key], FormData.model_validate(
        branch.target,
        context={"name": branch.name},
    )
