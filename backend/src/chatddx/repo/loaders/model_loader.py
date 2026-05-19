# src/chatddx/django/repo/models/loader.py
from django.db import IntegrityError
from django.db.models import Model as DjangoModel

from chatddx.repo.base import BaseFormData, TrailModel, TrailSchema
from chatddx.repo.branch_models import BranchModel
from chatddx.repo.main import Repo
from chatddx.repo.trail_schema_refs import (
    AgentSchemaRef,
    ToolGroupSchemaRef,
)
from chatddx.repo.trail_schemas import (
    AgentSchema,
    ToolGroupSchema,
)

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


def create_trail(schema: TrailSchema) -> DjangoModel:
    TM = Repo(schema, TrailModel)
    match schema:
        case AgentSchema():
            schema = _ref_agent(schema)
        case ToolGroupSchema():
            schema = _ref_tool_group(schema)
        case _:
            pass
    try:
        trail_instance, _ = TM.objects.get_or_create(
            fingerprint=schema.fingerprint,
            **schema.model_dump(exclude={"fingerprint"}),
        )
    except IntegrityError:
        trail_instance = TM.objects.get(fingerprint=schema.fingerprint)

    return trail_instance


def create_branch(
    schema: TrailSchema,
    name: str,
    owner_id: int,
) -> BranchModel:
    BM = Repo(schema, BranchModel)
    trail_instance = create_trail(schema)
    branch_instance = BM.objects.create(
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
) -> tuple[str, BaseFormData]:
    FD = Repo(schema, BaseFormData)
    branch = create_branch(
        schema,
        name,
        owner_id,
    )
    key_: str = {
        "id": branch.pk,
        "name": name,
    }[key]
    return key_, FD.model_validate(
        branch.target,
        context={"name": branch.name},
    )
