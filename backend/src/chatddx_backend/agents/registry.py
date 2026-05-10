# src/chatddx_backend/agents/registry.py
from __future__ import annotations

import json
from functools import reduce
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    TypeVar,
    cast,
    get_args,
    get_origin,
)

import tomli
from pydantic import (
    BaseModel,
    JsonValue,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
    model_validator,
)

FileLoaders = dict[str, Callable[[IO[bytes]], JsonValue]]

T = TypeVar("T", bound=BaseModel)


class ParseError(Exception):
    pass


class RegistryRecord(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def resolve(cls, data: Any, info: ValidationInfo) -> Any:
        if not info.context:
            return data

        record_type = info.context["cls"].get_field_by_type(cls)
        record = info.context["input"][record_type]

        base_data: dict[str, Any] = {}

        match data:
            case str():
                return {"name": data} | record[data]
            case list():
                base_data = record[data[0]] | {
                    "name": data[0],
                    "extends": data[1:],
                }
            case dict():
                base_data = cast(dict[str, Any], data.copy())
            case _:
                raise ParseError(f"bad data {data}")

        if not base_data.get("extends"):
            return base_data

        if isinstance(base_data["extends"], str):
            base_data["extends"] = [base_data["extends"]]

        for ext_name in base_data["extends"]:
            ext_data = record[ext_name]
            base_data["name"] += "|" + ext_name
            base_data = ext_data | base_data

        return base_data


class Registry(BaseModel):
    _path: Path | None = PrivateAttr(default=None)

    def get_by_type(self, RecordType: type[T], name: str) -> T:
        record_type = self.__class__.get_field_by_type(RecordType)
        try:
            return getattr(self, record_type)[name]
        except KeyError:
            raise KeyError(f"'{record_type}.{name}' doesn't exist in '{self._path}':")

    @model_validator(mode="before")
    @classmethod
    def attach_names_and_filter_out_partials(cls, data: Any) -> Any:
        result: dict[str, Any] = {}

        for record_type in cls.model_fields:
            if record_type not in data:
                continue

            result[record_type] = {}

            for name, values in data[record_type].items():
                if values.get("partial"):
                    continue
                result[record_type][name] = {"name": name} | values

        return result

    @classmethod
    def get_field_by_type(cls, schema_type: type[BaseModel]) -> str:
        if not hasattr(cls, "_cached_type_map"):
            cls._cached_type_map = {
                get_args(f.annotation)[-1]: name
                for name, f in cls.model_fields.items()
                if get_origin(f.annotation)
            }
        return cls._cached_type_map[schema_type]

    @classmethod
    def from_file(cls, path: Path):
        data = _from_file(path)
        try:
            instance = cls.model_validate(
                data,
                context={
                    "cls": cls,
                    "input": data,
                },
            )
        except ValidationError as e:
            for err in e.errors():
                loc = " -> ".join(str(e) for e in err["loc"])
                print(f"{loc}: {err['msg']} (got {err.get('input')!r})")
            raise

        instance._path = path
        return instance


def _from_file(
    path: Path,
    seen: list[Path] | None = None,
) -> JsonValue:
    if seen is None:
        seen = list()

    resolved_path = path.resolve()
    if resolved_path in seen:
        loop = " -> ".join([p.name for p in seen] + [path.name])
        raise ParseError(f"Circular dependency detected in 'extends': {loop}")

    current_seen = seen + [resolved_path]

    def txt(f: IO[bytes]) -> str:
        content = f.read().decode("utf-8").rstrip("\n")
        return content

    loaders: FileLoaders = {
        ".toml": tomli.load,
        ".json": json.load,
        ".txt": txt,
    }

    with path.open("rb") as f:
        data = resolve_imports(
            loaders[path.suffix](f), loaders, path.parent, current_seen
        )

    if not isinstance(data, dict):
        return data

    extends = cast(list[str] | str, data.get("extends", []))
    if isinstance(extends, str):
        extends = [extends]

    return reduce(
        extend_registries,
        [_from_file(path.parent / p, current_seen) for p in extends],
        data,
    )


def extend_registries(base: JsonValue, update: JsonValue):
    if not isinstance(base, dict) or not isinstance(update, dict):
        return base

    for key, value in update.items():
        if not isinstance(value, dict):
            continue
        base_val = base.get(key, {})
        if not isinstance(base_val, dict):
            raise ValueError(f"unexpected value in '{base}'")

        base[key] = value | base_val

    return base


def resolve_imports(
    obj: JsonValue,
    loaders: FileLoaders,
    base_path: Path,
    seen: list[Path] | None = None,
) -> JsonValue:

    if seen is None:
        seen = list()

    if isinstance(obj, dict):
        new_obj: dict[str, Any] = {}

        for key, value in obj.items():
            if key.endswith("_path"):
                if not isinstance(value, str):
                    raise ParseError(
                        f"*_path is expected to be a string, was '{value}'"
                    )

                key = key.replace("_path", "")

                if key in obj:
                    raise ParseError(
                        f"Both '{key}_path' and '{key}' are defined, pick one. '{obj}'"
                    )

                path = (base_path / value).resolve()

                if path in seen:
                    loop = " -> ".join([p.name for p in seen] + [path.name])
                    raise ParseError(
                        f"Circular dependency detected in 'extends': {loop}"
                    )

                with path.open("rb") as f:
                    value = loaders[path.suffix](f)

                new_obj[key] = resolve_imports(
                    value,
                    loaders,
                    path.parent,
                    seen + [path],
                )
            else:
                new_obj[key] = resolve_imports(
                    value,
                    loaders,
                    base_path,
                    seen,
                )
        return new_obj

    elif isinstance(obj, list):
        return [
            resolve_imports(
                item,
                loaders,
                base_path,
                seen,
            )
            for item in obj
        ]

    return obj
