# src/chatddx_backend/agents/trail/spec_loader.py
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

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

if TYPE_CHECKING:
    from chatddx_backend.agents.schemas import TrailRegistry, TrailSchemaT

SpecT = TypeVar("SpecT", bound=TrailSpec)
ModelT = TypeVar("ModelT", bound=TrailModel)

# Composed convenience functions


async def spec_from_registry(
    Spec: type[SpecT],
    name: str,
    registry: TrailRegistry,
) -> SpecT:
    schema = schema_from_registry(Spec.Model.Schema, name, registry)
    model = await model_from_schema(Spec.Model, schema)
    spec = spec_from_model(Spec, model)
    return spec


async def model_from_schema(
    Model: type[ModelT],
    schema: TrailSchema,
) -> ModelT:
    pk = await pk_from_schema(Model, schema)
    model = await model_from_pk(Model, pk)
    return model


# Atomic pipeline steps


def schema_from_registry(
    Schema: type[TrailSchemaT],
    name: str,
    registry: TrailRegistry,
) -> TrailSchemaT:
    return registry.get(Schema, name)


async def pk_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
) -> int:
    values = {}

    for key, value in schema:
        field = Model._meta.get_field(key)
        related_model = getattr(field, "related_model", None)

        match one_or_list_of(TrailSchema, value):
            case OneOf(v) if related_model:
                values[key + "_id"] = await pk_from_schema(related_model, v)

            case ListOf(vs) if related_model:
                tasks = [pk_from_schema(related_model, v) for v in vs]
                values[key] = await asyncio.gather(*tasks)

            case None:
                values[key] = value

            case _:
                raise ValueError(f"'{value}' is a relation but lacks related_model")

    pk = await Model(**values).apply()
    return pk


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
    Schema: type[TrailSchemaT],
    spec: TrailSpec,
) -> TrailSchemaT:
    return Schema.model_validate(spec.model_dump())
