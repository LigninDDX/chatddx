from typing import Any, TypeVar

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet

from chatddx.history.models import IdentityModel
from chatddx.repo import proxies
from chatddx.repo.base import (
    BaseFormDataIn,
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
    form_data: BaseFormDataIn,
) -> proxies.BranchProxy:

    Proxy = Repo(model_name, proxies.BranchProxy)
    TM = Repo(model_name, TrailModel)
    TS = Repo(model_name, TrailSchema)
    TSRef = Repo(model_name, TrailSchemaRef)

    schema_in = TS.model_validate(form_data.model_dump())

    schema_ref = TSRef.from_schema(schema_in)

    trail, _ = TM.objects.get_or_create(
        fingerprint=schema_ref.fingerprint,
        defaults=schema_ref.model_dump(),
    )

    canon = qs_canon(
        Proxy.objects.filter(name=form_data.name),
        owner_name,
    ).first()

    if canon and schema_ref.fingerprint == canon.target.fingerprint:
        return canon  # pyright: ignore

    proxy = Proxy(
        target=trail,  # pyright: ignore
        owner=IdentityModel.objects.get(name=owner_name),  # pyright: ignore
        name=form_data.name,  # pyright: ignore
    )
    return proxy


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
