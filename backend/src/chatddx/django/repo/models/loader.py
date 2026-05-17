# src/chatddx/django/repo/models/loader.py
from typing import TypeVar

from django.db import IntegrityError
from django.db.models import Model as DjangoModel
from repo.models import (
    AgentModel,
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
    ToolModel,
)
from repo.models.history import (
    AgentBranchModel,
    BranchModel,
    ConnectionBranchModel,
    OutputTypeBranchModel,
    SamplingParamsBranchModel,
    ToolBranchModel,
    ToolGroupBranchModel,
)
from repo.trail.models import TrailModel

from chatddx.django.repo.admin.schemas import (
    AgentFormData,
    BranchFormData,
    ConnectionFormData,
    OutputTypeFormData,
    SamplingParamsFormData,
    ToolFormData,
    ToolGroupFormData,
)
from chatddx.django.repo.schemas import (
    AgentSchema,
    AgentSchemaRef,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolGroupSchemaRef,
    ToolSchema,
)
from chatddx.django.repo.trail import TrailSchema

model_map: dict[
    type[TrailSchema],
    tuple[
        type[DjangoModel],
        type[BranchModel],
        type[BranchFormData],
    ],
] = {
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

agent_relations: list[str] = [
    "connection",
    "sampling_params",
    "output_type",
    "tool_group",
]


def _ref_tool_group(schema: ToolGroupSchema) -> ToolGroupSchemaRef:
    tool_ids = [create_trail(tool).pk for tool in schema.tools]
    return ToolGroupSchemaRef(**(schema.model_dump() | {"tools": tool_ids}))


def _ref_agent(schema: TrailSchema):
    ref_ids = {
        ref + "_id": create_trail(getattr(schema, ref)).pk for ref in agent_relations
    }
    return AgentSchemaRef(**schema.model_dump(exclude=set(agent_relations)) | ref_ids)


TrailSchemaT = TypeVar("TrailSchemaT", bound=TrailSchema)


def create_trail(schema: TrailSchema) -> DjangoModel:
    _TrailModel, _, _ = model_map[type(schema)]
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
        trail_instance = _TrailModel.objects.get(fingerprint=schema.fingerprint)

    return trail_instance


def create_branch(
    schema: TrailSchema,
    name: str,
    owner_id: int,
) -> BranchModel:
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
) -> tuple[str, BranchFormData]:
    _, _, FormData = model_map[type(schema)]
    branch = create_branch(
        schema,
        name,
        owner_id,
    )
    key_: str = {
        "id": branch.pk,
        "name": name,
    }[key]
    return key_, FormData.model_validate(
        branch.target,
        context={"name": branch.name},
    )
