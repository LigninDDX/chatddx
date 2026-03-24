# src/chatddx_backend/agents/spec_loader.py
import asyncio
from typing import Any, TypeVar

from django.db.models import ForeignKey

from chatddx_backend.agents.registry import parse_registry
from chatddx_backend.agents.trail import (
    TrailModel,
    TrailSchema,
    TrailSpec,
    resolve_related_array_fields,
)
from chatddx_backend.agents.utils import (
    ListOf,
    OneOf,
    classify_value,
)

SchemaT = TypeVar("SchemaT", bound=TrailSchema)
SpecT = TypeVar("SpecT", bound=TrailSpec)
ModelT = TypeVar("ModelT", bound=TrailModel)

# Composed convenience functions


def schema_from_registry(
    Schema: type[SchemaT],
    name: str,
    registry: dict[str, Any],
) -> SchemaT:
    data = data_from_registry(Schema, name, registry)
    schema = schema_from_data(Schema, data)
    return schema


async def model_from_schema(
    Model: type[ModelT],
    schema: TrailSchema,
) -> ModelT:
    pk = await pk_from_schema(Model, schema)
    model = await model_from_pk(Model, pk)
    return model


# Atomic pipeline steps


def data_from_registry(
    Schema: type[TrailSchema],
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    return parse_registry(Schema, name, registry)


def schema_from_data(
    Schema: type[SchemaT],
    data: dict[str, Any],
) -> SchemaT:
    return Schema.model_validate(data)


async def pk_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
) -> int:
    values = {}

    for key, value in schema:
        field = Model._meta.get_field(key)
        related_model = getattr(field, "related_model", None)
        relation_type = classify_value(TrailSchema, value)

        match relation_type:
            case OneOf(_) if related_model:
                values[key + "_id"] = await pk_from_schema(related_model, value)

            case ListOf(_) if related_model:
                tasks = [pk_from_schema(related_model, v) for v in value]
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
    Schema: type[SchemaT],
    spec: TrailSpec,
) -> SchemaT:
    return Schema.model_validate(spec.model_dump())
