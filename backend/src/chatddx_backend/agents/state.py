# src/chatddx_backend/agents/state.py
from typing import Any, TypeVar

from chatddx_backend.agents.models import TrailModel
from chatddx_backend.agents.registry import data_from_registry
from chatddx_backend.agents.schema import TrailInSchema, TrailOutSchema
from chatddx_backend.agents.utils import (
    ListField,
    SingleField,
    value_is_or_list_of,
)


def process_from_registry(
    Model: type[TrailModel],
    name: str,
    registry: dict[str, Any],
) -> TrailOutSchema:
    data = data_from_registry(Model.schema_in, name, registry)
    return process_from_data(Model, data)


def process_from_data(
    Model: type[TrailModel],
    data: dict[str, Any],
) -> TrailOutSchema:
    schema = schema_from_data(Model.schema_in, data)
    model = model_from_schema(Model, schema)
    return Model.schema_out.model_validate(model)


def model_from_data(
    Model: type[TrailModel],
    data: dict[str, Any],
) -> TrailModel:
    schema = schema_from_data(Model.schema_in, data)
    return model_from_schema(Model, schema)


T = TypeVar("T", bound=TrailInSchema)


def schema_from_registry(
    Schema: type[T],
    name: str,
    registry: dict[str, Any],
) -> T:
    data = data_from_registry(Schema, name, registry)
    return schema_from_data(Schema, data)


def schema_from_data(
    Schema: type[T],
    data: dict[str, Any],
) -> T:
    return Schema.model_validate(data)


def model_from_schema(
    Model: type[TrailModel],
    data: TrailInSchema,
) -> TrailModel:
    values = {}

    for key, value in data:
        field = Model._meta.get_field(key)
        related_model = getattr(field, "related_model", None)

        match value_is_or_list_of(TrailInSchema, value):
            case SingleField() if related_model:
                values[key] = model_from_schema(related_model, value)
            case ListField() if related_model:
                values[key] = [model_from_schema(related_model, v) for v in value]
            case None:
                values[key] = value
            case _:
                raise ValueError(f"'{value}' is a relation but lacks related_model")

    return Model.apply(**values)
