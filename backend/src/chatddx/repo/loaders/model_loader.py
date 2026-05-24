# src/chatddx/django/repo/models/loader.py
from typing import Any, TypeVar, get_args

from django.db import IntegrityError
from django.db.models import Model as DjangoModel
from django.db.models import OuterRef, Q, QuerySet, Subquery
from pydantic import BaseModel

from chatddx.repo.base import (
    BaseFormDataOut,
    BranchModel,
    TrailModel,
    TrailSchema,
    TrailSchemaRef,
)
from chatddx.repo.form_data_out import (
    AgentFormDataOut,
    ConnectionFormDataOut,
    OutputTypeFormDataOut,
    SamplingParamsFormDataOut,
    TemplateData,
    ToolFormDataOut,
    ToolGroupFormDataOut,
)
from chatddx.repo.main import BundleName, Repo

agent_relations: list[BundleName] = [
    "connection",
    "sampling_params",
    "output_type",
    "tool_group",
]


def get_owned_trails(model: str, owner_name: str) -> dict[str, BaseFormDataOut]:
    BM = Repo(model, BranchModel)
    FD = Repo(model, BaseFormDataOut)
    TM = Repo(model, TrailModel)

    indirectly_owned = Q(agenttrailmodel__branches__owner__name=owner_name)
    directly_owned = Q(branches__owner__name=owner_name)

    match model:
        case "tool":
            owned = directly_owned
        case "agent":
            owned = directly_owned
        case _:
            owned = directly_owned | indirectly_owned

    branches = qs_canon(BM.objects.all(), owner_name)

    branchless_trails = (
        TM.objects.filter(owned).filter(branches__isnull=True).distinct()
    )

    form_data: dict[str, BaseFormDataOut] = {}
    for branch in branches:
        form_data[str(branch.target.pk)] = FD.model_validate(
            branch.target,
            context={"name": branch.name},
        )
    for trail in branchless_trails:
        form_data[str(trail.pk)] = FD.model_validate(
            trail,
            context={"name": trail.fingerprint[:6]},
        )
    return form_data


def get_named_trails(model_name: BundleName, qs: QuerySet[TrailModel]):
    TM = Repo(model_name, TrailModel)
    branch_subquery = TM.objects.filter(pk=OuterRef("pk")).values("branches__name")[:1]
    return (
        TM.objects.filter(pk__in=list(owned_relation.keys()))
        .annotate(branch_name=Subquery(branch_subquery))
        .distinct()
    )


def get_template_data(owner_name: str):
    payload: dict[BundleName, Any] = {
        model: get_owned_trails(model, owner_name) for model in get_args(BundleName)
    }
    td = TemplateData.model_validate(payload)
    return td.model_dump_json(by_alias=True)


DjangoModelT = TypeVar("DjangoModelT", bound=DjangoModel)


def qs_canon(qs: QuerySet[DjangoModelT], owner_name: str) -> QuerySet[DjangoModelT]:
    return (
        qs.filter(owner__name=owner_name)
        .order_by("owner_id", "name", "-timestamp")
        .distinct("owner_id", "name")
    )


def qs_super_agent(qs: QuerySet[DjangoModelT], owner_name: str):
    def subquery(owner_name: str, model: str, column: str):
        BM = Repo(model, BranchModel)

        return BM.objects.filter(
            target=OuterRef(f"target__{model}"),
            owner__name=owner_name,
        ).values(column)[:1]

    branch_annotations = {
        f"{model}_{field}": Subquery(subquery(owner_name, model, field))
        for field in ("name", "id")
        for model in agent_relations
    }
    return qs.select_related(
        *[f"target__{model}" for model in agent_relations]
    ).annotate(**branch_annotations)


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
