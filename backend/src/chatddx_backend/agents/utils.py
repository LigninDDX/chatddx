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
)

from pydantic.fields import FieldInfo

T = TypeVar("T")

JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None
JSONLoaders = dict[str, Callable[[IO[bytes]], JSONValue]]


@dataclass
class SingleField(Generic[T]):
    t: type[T]


@dataclass
class ListField(Generic[T]):
    t: type[T]


IsOrListOf = SingleField[T] | ListField[T] | None


type TypeTree = type | tuple[Any, list["TypeTree"]]


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries, update overwrites base."""
    merged = base.copy()
    for k, v in update.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], cast(dict[str, Any], v))
        else:
            merged[k] = v
    return merged


def type_sig(t: type) -> TypeTree:
    origin = get_origin(t)
    args = get_args(t)

    if not origin and not args:
        return t

    if origin is Union:
        return (Union, [type_sig(a) for a in args])

    assert origin is not None
    return (origin, [type_sig(a) for a in args])


def sig_to_str(tree: TypeTree) -> str:
    def shorten(v: Any):
        return {
            "UnionType": "U",
            "NoneType": "None",
        }.get(str(v), str(v))

    if isinstance(tree, tuple):
        origin, children = tree
        child_strs = "_".join(shorten(sig_to_str(c)) for c in children)
        name = shorten(getattr(origin, "__name__", str(origin)))
        return f"{name}_{child_strs}"
    return getattr(tree, "__name__", str(tree))


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


def resolve_paths(obj: JSONValue, loaders: JSONLoaders, root: Path) -> Any:
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
                resolve_paths(value, loaders, root)
    elif isinstance(obj, list):
        for item in obj:
            resolve_paths(item, loaders, root)
    return obj
