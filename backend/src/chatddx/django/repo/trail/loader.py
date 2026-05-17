# src/chatddx_backend/agents/trail/loader.py
from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from django.db.models import ForeignKey
from repo.trail.models import (
    TrailModel,
    resolve_related_array_fields,
)

from chatddx.django.repo.trail.schemas import (
    TrailSchema,
    TrailSpec,
)
from chatddx.django.repo.utils import (
    ListOf,
    OneOf,
    one_or_list_of,
)

SchemaT = TypeVar("SchemaT", bound=TrailSchema)
ModelT = TypeVar("ModelT", bound=TrailModel)
SpecT = TypeVar("SpecT", bound=TrailSpec)

# Composed convenience functions


async def model_from_schema(
    Model: type[ModelT],
    schema: TrailSchema,
) -> ModelT:
    pk = await pk_from_schema(Model, schema)
    model = await model_from_pk(Model, pk)
    return model


# Atomic pipeline steps


async def pk_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
) -> int:
    new_values: dict[str, Any] = {}

    for field_name, field_value in schema:
        field = Model._meta.get_field(field_name)
        associated_model = (
            getattr(field, "associated_model", None) or field.related_model
        )

        match one_or_list_of(TrailSchema, field_value):
            case OneOf(value) if associated_model:
                new_values[field_name + "_id"] = await pk_from_schema(
                    associated_model,
                    value,
                )

            case ListOf(values) if associated_model:
                new_values[field_name] = await asyncio.gather(
                    *[
                        pk_from_schema(
                            associated_model,
                            value,
                        )
                        for value in values
                    ]
                )

            case None:
                new_values[field_name] = field_value

            case _:
                raise ValueError(
                    f"'{field_value}' is a relation but lacks associated model"
                )

    model, _ = await Model.objects.aget_or_create(
        fingerprint=schema.fingerprint,
        defaults=new_values,
    )

    return model.pk


async def model_from_pk(
    Model: type[ModelT],
    pk: int,
) -> ModelT:
    related = [f.name for f in Model._meta.get_fields() if isinstance(f, ForeignKey)]
    model = await Model.objects.select_related(*related).aget(pk=pk)
    await resolve_related_array_fields(model)
    return model


def spec_from_model(
    Spec: type[SpecT],
    model: TrailModel,
) -> SpecT:
    return Spec.model_validate(model)
