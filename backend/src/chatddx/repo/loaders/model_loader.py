# src/chatddx/django/repo/models/loader.py
from django.db import IntegrityError
from django.db.models import Model as DjangoModel

from chatddx.repo.base import BaseFormDataOut, TrailModel, TrailSchema, TrailSchemaRef
from chatddx.repo.branch_models import BranchModel
from chatddx.repo.main import Repo

agent_relations: list[str] = [
    "connection",
    "sampling_params",
    "output_type",
    "tool_group",
]


def create_trail(schema: TrailSchema) -> DjangoModel:
    TM = Repo(schema, TrailModel)
    TSRef = Repo(schema, TrailSchemaRef)

    schema_ref = TSRef.from_schema(schema)
    try:
        trail_instance, _ = TM.objects.get_or_create(
            fingerprint=schema_ref.fingerprint,
            **schema_ref.model_dump(exclude={"fingerprint"}),
        )
    except IntegrityError:
        trail_instance = TM.objects.get(fingerprint=schema_ref.fingerprint)

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
) -> tuple[str, BaseFormDataOut]:
    FD = Repo(schema, BaseFormDataOut)
    branch = create_branch(
        schema,
        name,
        owner_id,
    )
    key_: str = {
        "id": str(branch.pk),
        "name": name,
    }[key]
    return key_, FD.model_validate(
        branch.target,
        context={"name": branch.name},
    )
