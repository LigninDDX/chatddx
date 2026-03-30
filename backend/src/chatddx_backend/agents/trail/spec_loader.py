# src/chatddx_backend/agents/trail/spec_loader.py
from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from django.db import IntegrityError
from django.db.models import ForeignKey

from chatddx_backend.agents.trail import (
    TrailModel,
    TrailSchema,
    TrailSpec,
    resolve_related_array_fields,
)
from chatddx_backend.agents.utils import (
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
    mutable: bool = False,
) -> ModelT:
    pk = await pk_from_schema(Model, schema, mutable)
    model = await model_from_pk(Model, pk)
    return model


# Atomic pipeline steps


async def pk_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
    mutable: bool = False,
) -> int:
    new_values: dict[str, Any] = {}

    for field_name, field_value in schema:
        field = Model._meta.get_field(field_name)
        related_model = getattr(field, "related_model", None)

        match one_or_list_of(TrailSchema, field_value):
            case OneOf(value) if related_model:
                new_values[field_name + "_id"] = await pk_from_schema(
                    related_model,
                    value,
                    mutable,
                )

            case ListOf(values) if related_model:
                new_values[field_name] = await asyncio.gather(
                    *[
                        pk_from_schema(
                            related_model,
                            value,
                            mutable,
                        )
                        for value in values
                    ]
                )

            case None:
                new_values[field_name] = field_value

            case _:
                raise ValueError(
                    f"'{field_value}' is a relation but lacks related_model"
                )

    name = new_values.pop("name")

    try:
        model, _ = await Model.objects.aget_or_create(
            name=name,
            fingerprint=schema.fingerprint,
            **new_values,
        )
    except IntegrityError:
        model = await Model.objects.aget(
            name=name,
            fingerprint=schema.fingerprint,
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


def schema_from_spec(
    Schema: type[SchemaT],
    spec: TrailSpec,
) -> SchemaT:
    return Schema.model_validate(spec.model_dump())
