import inspect
from dataclasses import dataclass
from pathlib import Path
from types import UnionType
from typing import (
    IO,
    Any,
    Callable,
    Generic,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo

JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None
JSONLoaders = dict[str, Callable[[IO[bytes]], JSONValue]]

T = TypeVar("T")


@dataclass
class SingleField(Generic[T]):
    t: type[T]


@dataclass
class ListField(Generic[T]):
    t: type[T]


IsOrListOf = SingleField[T] | ListField[T] | None


type TypeTree = type | tuple[Any, list["TypeTree"]]


def describe_function(
    func: Callable[..., Any],
) -> tuple[dict[str, Any] | None, str | None]:
    sig = inspect.signature(func)
    docstring = inspect.getdoc(func)
    hints = get_type_hints(func)

    name, _ = next(iter(sig.parameters.items()))
    model = hints[name]

    if len(sig.parameters.values()) != 1 or not issubclass(model, BaseModel):
        return None, docstring

    return model.model_json_schema(), docstring


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries, update overwrites base."""
    merged = base.copy()
    for k, v in update.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], cast(dict[str, Any], v))
        else:
            merged[k] = v
    return merged


def value_is_or_list_of(t: type[T], value: object) -> IsOrListOf[T]:
    if isinstance(value, t):
        return SingleField(t)

    if isinstance(value, list):
        if not value or isinstance(value[0], t):
            return ListField(t)


def field_is_or_list_of(t: type[T], field: FieldInfo) -> IsOrListOf[T]:
    ann = field.annotation
    origin = get_origin(ann)

    if origin is Union or origin is UnionType:
        args = [a for a in get_args(ann) if a is not type(None)]
        ann = args[0] if len(args) == 1 else ann

    if isinstance(ann, type) and issubclass(ann, t):
        return SingleField(ann)

    if origin is list:
        inner = get_args(ann)
        if inner and isinstance(inner[0], type) and issubclass(inner[0], t):
            return ListField(inner[0])


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
