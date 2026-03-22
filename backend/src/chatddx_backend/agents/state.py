# src/chatddx_backend/agents/state.py
import json
from pathlib import Path
from typing import Any, TypeVar, cast

import tomli

from chatddx_backend.agents.models import TrailModel
from chatddx_backend.agents.schema import TrailInSchema, TrailOutSchema
from chatddx_backend.agents.utils import (
    JSONLoaders,
    ListField,
    SingleField,
    deep_merge,
    field_is_or_list_of,
    resolve_paths,
    value_is_or_list_of,
)

S = TypeVar("S", bound=TrailOutSchema)
T = TypeVar("T", bound=TrailInSchema)


def load_registry(file_path: Path) -> Any:
    loaders: JSONLoaders = {
        ".toml": tomli.load,
        ".json": json.load,
        ".txt": lambda f: f.read().decode("utf-8"),
    }
    with file_path.open("rb") as f:
        data = loaders[file_path.suffix](f)
    return resolve_paths(data, loaders, file_path.parent)


def process(
    Model: type[TrailModel],
    data: dict[str, Any],
) -> TrailOutSchema:
    schema_in = as_schema_in(Model.schema_in, data)
    model_instance = as_model_instance(Model, schema_in)
    return as_schema_out(Model.schema_out, model_instance)


def from_registry(
    Model: type[TrailModel],
    name: str,
    registry: dict[str, Any],
) -> TrailOutSchema:
    data = parse_registry(Model.schema_in, name, registry)
    return process(Model, data)


def parse_registry(
    Schema: type[TrailInSchema],
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    raw_values = registry[Schema.record_type][name].copy()
    values = {}

    if "extends" in raw_values:
        for base_name in raw_values.pop("extends"):
            base_values = parse_registry(Schema, base_name, registry)
            values = deep_merge(values, base_values)

    values = deep_merge(values, raw_values)
    values["name"] = name

    for field_name, field_info in Schema.model_fields.items():
        if field_name not in values:
            continue
        match field_is_or_list_of(TrailInSchema, field_info):
            case SingleField(t):
                values[field_name] = parse_registry(t, values[field_name], registry)
            case ListField(t):
                values[field_name] = [
                    parse_registry(t, item_name, registry)
                    for item_name in cast(list[str], values[field_name])
                ]
            case None:
                pass

    return values


def as_schema_in(
    Schema: type[T],
    data: dict[str, Any],
) -> T:
    return Schema.model_validate(data)


def as_schema_out(
    Schema: type[S],
    model_instance: TrailModel,
) -> S:
    return Schema.model_validate(model_instance)


def as_model_instance(
    Model: type[TrailModel],
    data: TrailInSchema,
) -> TrailModel:
    values = {}

    for key, value in data:
        field = Model._meta.get_field(key)
        related_model = getattr(field, "related_model", None)

        match value_is_or_list_of(TrailInSchema, value):
            case SingleField() if related_model:
                values[key] = as_model_instance(related_model, value)
            case ListField() if related_model:
                values[key] = [as_model_instance(related_model, v) for v in value]
            case None:
                values[key] = value
            case _:
                raise ValueError(f"'{value}' is a relation but lacks related_model")

    return Model.apply(**values)
