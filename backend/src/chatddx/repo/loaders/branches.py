from typing import Any, TypeVar

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet

from chatddx.history.models import IdentityModel
from chatddx.repo import proxies
from chatddx.repo.base import (
    BaseFormData,
    BranchModel,
    BranchSchema,
    TrailModel,
    TrailSchema,
)
from chatddx.repo.loaders.trail import pk_from_schema
from chatddx.repo.main import BundleName, Repo
from chatddx.repo.trail_schema_refs import TrailSchemaRef

TrailSchemaT = TypeVar("TrailSchemaT", bound=TrailSchema)


def asdf(model_name: str, pk: int) -> TrailSchema:
    model = Repo(model_name, TrailModel).objects.select_related().get(pk=pk)
    return Repo(model_name, TrailSchema).model_validate(model)


def get_branch_model(
    model_name: BundleName,
    owner_name: str,
    data: dict[str, Any],
) -> proxies.BranchProxy:

    Proxy = Repo(model_name, proxies.BranchProxy)
    TM = Repo(model_name, TrailModel)
    TS = Repo(model_name, TrailSchema)
    TSRef = Repo(model_name, TrailSchemaRef)

    form_data = Repo(model_name, BaseFormData).model_validate(data)

    schema_ref = TSRef.model_validate(form_data.model_dump(exclude_none=True))

    relations = {
        field_ref: asdf(field_ref, getattr(schema_ref, field_ref))
        for field_ref in TSRef.__annotations__
    }
    schema = TS.model_validate(schema_ref.model_dump() | relations)

    name = data.get("name", "")

    trail, _ = TM.objects.get_or_create(
        fingerprint=schema.fingerprint,
        defaults=schema.model_dump(),
    )

    canon = qs_canon(
        Proxy.objects.filter(name=name),
        owner_name,
    ).first()

    if canon and schema.fingerprint == canon.target.fingerprint:
        return canon  # pyright: ignore

    return Repo(model_name, proxies.BranchProxy)(
        target=trail,  # pyright: ignore
        owner=IdentityModel.objects.get(name=owner_name),  # pyright: ignore
        name=name,  # pyright: ignore
    )


DjangoModelT = TypeVar("DjangoModelT", bound=DjangoModel)


def qs_canon(qs: QuerySet[DjangoModelT], owner_name: str) -> QuerySet[DjangoModelT]:
    return (
        qs.filter(owner__name=owner_name)
        .order_by("owner_id", "name", "-timestamp")
        .distinct("owner_id", "name")
    )


async def get_branch_model_async(
    name: str,
    owner_id: int,
    trail_schema: TrailSchema,
) -> BranchModel:
    branch_schema = await get_branch_schema(name, owner_id, trail_schema)
    branch_model = await model_from_schema(branch_schema)
    return branch_model


async def get_branch_schema(
    name: str,
    owner_id: int,
    trail_schema: TrailSchemaT,
) -> BranchSchema[TrailSchemaT]:
    return BranchSchema[TrailSchemaT](
        name=name,
        owner_id=owner_id,
        target_type=type(trail_schema),
        target_id=await pk_from_schema(
            Repo(
                type(trail_schema),
                TrailModel,
            ),
            trail_schema,
        ),
    )


async def model_from_schema(
    schema: BranchSchema[TrailSchemaT],
) -> BranchModel:
    trail_model_class = Repo(schema.target_type, TrailModel)
    branch_model_class = trail_model_class.branches.rel.related_model  # pyright: ignore
    instance, _ = await branch_model_class.objects.aget_or_create(  # pyright: ignore
        owner_id=schema.owner_id,
        name=schema.name,
        target_id=schema.target_id,
    )
    return instance  # pyright: ignore
