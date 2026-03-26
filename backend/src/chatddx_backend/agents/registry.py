# src/chatddx_backend/agents/registry.py
from __future__ import annotations

import json
from functools import reduce
from pathlib import Path
from typing import IO, Any, Callable, TypeVar, cast, get_args, get_origin

import tomli
from pydantic import (
    BaseModel,
    JsonValue,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
    model_validator,
)

from chatddx_backend.agents.utils import ListOf, OneOf, one_or_list_of

FileLoaders = dict[str, Callable[[IO[bytes]], JsonValue]]


class ParseError(Exception):
    pass


class RegistryRecord(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def resolve(cls, data: Any, info: ValidationInfo) -> Any:
        if not info.context:
            return data

        record_type = info.context["cls"].get_field_by_type(cls)
        base_data: dict[str, Any] = {}
        refs: list[str] = []

        if isinstance(data, dict):
            base_data = cast(dict[str, Any], data.copy())

            if not isinstance(base_data.get("name"), str):
                raise ParseError(f"dict instances must have 'name'")

            match one_or_list_of(str, base_data.get("extends")):
                case OneOf(value):
                    refs = [value]
                case ListOf(values):
                    refs = values
                case None:
                    return base_data

            base_data["name"] += "|" + "|".join(refs)

        else:
            match one_or_list_of(str, data):
                case OneOf(value):
                    refs = [value]
                case ListOf(values):
                    refs = values
                case None:
                    raise ParseError(f"bad data {data}")

            base_data["name"] = "|".join(refs)

        for ref in refs:
            try:
                ref_value = info.context["input"][record_type][ref]
            except KeyError:
                raise ParseError(f"ref missing: {ref}")

            base_data = ref_value | base_data

        return base_data


T = TypeVar("T", bound=BaseModel)


class Registry(BaseModel):
    _path: Path | None = PrivateAttr(default=None)

    def get(self, RecordType: type[T], name: str) -> T:
        record_type = self.__class__.get_field_by_type(RecordType)
        try:
            return getattr(self, record_type)[name]
        except KeyError:
            raise KeyError(f"'{record_type}.{name}' doesn't exist in '{self._path}':")

    @model_validator(mode="before")
    @classmethod
    def first_pass(cls, data: Any) -> Any:
        resolved_data: dict[str, Any] = {}

        for record_type in cls.model_fields:
            if record_type not in data:
                continue

            resolved_data[record_type] = {}

            for name, values in data[record_type].items():
                if values.get("partial"):
                    continue
                resolved_data[record_type][name] = {"name": name} | values

        return resolved_data

    @classmethod
    def _type_map(cls) -> dict[type[BaseModel], str]:
        if not hasattr(cls, "_cached_type_map"):
            cls._cached_type_map = {
                get_args(f.annotation)[-1]: name
                for name, f in cls.model_fields.items()
                if get_origin(f.annotation)
            }
        return cls._cached_type_map

    @classmethod
    def get_field_by_type(cls, schema_type: type[BaseModel]) -> str:
        field_name = cls._type_map().get(schema_type)
        if field_name is None:
            raise KeyError(f"No field holds {schema_type.__name__}")
        return field_name

    @classmethod
    def from_file(cls, path: Path):
        data = cls._from_file(path)
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
                loc = " -> ".join(str(x) for x in err["loc"])
                print(f"  {loc}: {err['msg']} (got {err.get('input')!r})")
            raise

        instance._path = path
        return instance

    @classmethod
    def _from_file(cls, path: Path, seen: list[Path] | None = None) -> JsonValue:
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

        data = reduce(
            cls.extend_registries,
            [cls._from_file(path.parent / p, current_seen) for p in extends],
            data,
        )
        return data

    @classmethod
    def extend_registries(cls, base: JsonValue, update: JsonValue):
        if not (isinstance(base, dict) and isinstance(update, dict)):
            return base

        for record_type in cls.model_fields:
            if not isinstance(update.get(record_type), dict):
                continue

            record_update = cast(dict[str, Any], update[record_type])

            if not isinstance(base.get(record_type, {}), dict):
                raise ValueError(f"unexpected value in '{base}'")

            for name, values in record_update.items():
                cast(dict[str, Any], base[record_type]).setdefault(name, values)

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
        for key in list(obj.keys()):
            value = obj[key]
            if key.endswith("_path") and isinstance(value, str):
                new_key = key.replace("_path", "")

                if new_key in obj:
                    raise ParseError(
                        f"Both '{key}' and '{new_key}' are defined, pick one. '{obj}'"
                    )

                path = (base_path / value).resolve()

                if path in seen:
                    loop = " -> ".join([p.name for p in seen] + [path.name])
                    raise ParseError(
                        f"Circular dependency detected in 'extends': {loop}"
                    )

                current_seen = seen + [path]

                with path.open("rb") as linked_file:
                    obj[new_key] = resolve_imports(
                        loaders[path.suffix](linked_file),
                        loaders,
                        path.parent,
                        current_seen,
                    )
                del obj[key]
            else:
                resolve_imports(
                    value,
                    loaders,
                    base_path,
                    seen,
                )

    elif isinstance(obj, list):
        for item in obj:
            resolve_imports(
                item,
                loaders,
                base_path,
                seen,
            )

    return obj
