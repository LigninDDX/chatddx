# src/chatddx_backend/agents/registry.py
import json
from pathlib import Path
from typing import IO, Any, cast

import tomli

from chatddx_backend.agents.schema import TrailSchema
from chatddx_backend.agents.utils import (
    JSONLoaders,
    ListField,
    SingleField,
    deep_merge,
    field_is_or_list_of,
    resolve_imports,
)


def data_from_registry(
    Schema: type[TrailSchema],
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    raw_values = registry[Schema.record_type][name].copy()
    values = {}

    if "extends" in raw_values:
        for base_name in raw_values.pop("extends"):
            base_values = data_from_registry(Schema, base_name, registry)
            values = deep_merge(values, base_values)

    values = deep_merge(values, raw_values)
    values["name"] = name

    for field_name, field_info in Schema.model_fields.items():
        if field_name not in values:
            continue
        match field_is_or_list_of(TrailSchema, field_info):
            case SingleField(t):
                values[field_name] = data_from_registry(t, values[field_name], registry)
            case ListField(t):
                values[field_name] = [
                    data_from_registry(t, item_name, registry)
                    for item_name in cast(list[str], values[field_name])
                ]
            case None:
                pass

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
