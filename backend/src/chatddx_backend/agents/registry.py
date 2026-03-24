# src/chatddx_backend/agents/registry.py
import json
from pathlib import Path
from typing import IO, Any, Callable, cast

import tomli

from chatddx_backend.agents.trail import TrailSchema
from chatddx_backend.agents.utils import (
    ListOf,
    OneOf,
    classify_field,
)

JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None
JSONLoaders = dict[str, Callable[[IO[bytes]], JSONValue]]


class ParseError(Exception):
    pass


def parse_registry(
    Schema: type[TrailSchema],
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    try:
        raw_values = registry[Schema.record_type][name].copy()
    except Exception:
        raise ParseError(
            f"field '{Schema.record_type}.{name}' does not exist in registry."
        )

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

        relation_type = classify_field(TrailSchema, field_info)

        relations: list[str]

        match relation_type:
            case None:
                continue
            case OneOf(relation_schema):
                relations = [values[field_name]]
            case ListOf(relation_schema):
                relations = values[field_name]

        def resolve_relations():
            for relation in relations:
                try:
                    _ = registry[relation_schema.record_type][relation]
                except Exception:
                    raise ParseError(
                        f"field '{Schema.record_type}.{field_name}' is a relation to "
                        f"'{relation_schema.record_type}' but its value '{relation}' is "
                        "not in registry."
                    )
                yield parse_registry(relation_schema, relation, registry)

        match relation_type:
            case OneOf(relation_schema):
                (values[field_name],) = resolve_relations()
            case ListOf(relation_schema):
                values[field_name] = list(resolve_relations())

    return values


def load_registry(file_path: Path, _seen: set[Path] | None = None) -> Any:
    if _seen is None:
        _seen = set()

    if file_path.resolve() in _seen:
        raise RecursionError(f"Circular dependency detected in config: {file_path}")
    _seen.add(file_path.resolve())

    def txt(f: IO[bytes]) -> str:
        content = f.read().decode("utf-8").rstrip("\n")
        return content

    loaders: JSONLoaders = {
        ".toml": tomli.load,
        ".json": json.load,
        ".txt": txt,
    }

    with file_path.open("rb") as f:
        data = loaders[file_path.suffix](f)

    if not isinstance(data, dict):
        raise TypeError("root level data must be dict")

    merged_data: dict[str, Any] = {}

    if "extends" in data and isinstance(data["extends"], (str, list)):
        extends_list = data.pop("extends")
        if isinstance(extends_list, str):
            extends_list = [extends_list]

        for base_file in cast(list[str], extends_list):
            base_data = load_registry(file_path.parent / base_file, _seen)
            merged_data = deep_merge(merged_data, base_data)

    merged_data = deep_merge(merged_data, data)

    return resolve_imports(merged_data, loaders, file_path.parent)


def resolve_imports(obj: JSONValue, loaders: JSONLoaders, root: Path) -> Any:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            value = obj[key]
            if key.endswith("_path") and isinstance(value, str):
                new_key = key.replace("_path", "")
                path = root / value
                with path.open("rb") as linked_file:
                    obj[new_key] = loaders[path.suffix](linked_file)
                del obj[key]
            else:
                resolve_imports(value, loaders, root)
    elif isinstance(obj, list):
        for item in obj:
            resolve_imports(item, loaders, root)
    return obj


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()
    for k, v in update.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], cast(dict[str, Any], v))
        else:
            merged[k] = v
    return merged
