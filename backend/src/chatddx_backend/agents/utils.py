# src/chatddx_backend/agents/utils.py
from dataclasses import dataclass
from types import UnionType
from typing import (
    Generic,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic.fields import FieldInfo

T = TypeVar("T")


@dataclass
class OneOf(Generic[T]):
    t: type[T]


@dataclass
class ListOf(Generic[T]):
    t: type[T]


def classify_value(t: type[T], value: object) -> OneOf[T] | ListOf[T] | None:
    if isinstance(value, t):
        return OneOf(t)

    if isinstance(value, list):
        if not value or isinstance(value[0], t):
            return ListOf(t)


def classify_field(t: type[T], field: FieldInfo) -> OneOf[T] | ListOf[T] | None:
    ann = field.annotation
    origin = get_origin(ann)

    if origin is Union or origin is UnionType:
        args = [a for a in get_args(ann) if a is not type(None)]
        ann = args[0] if len(args) == 1 else ann

    if isinstance(ann, type) and issubclass(ann, t):
        return OneOf(ann)

    if origin is list:
        inner = get_args(ann)
        if inner and isinstance(inner[0], type) and issubclass(inner[0], t):
            return ListOf(inner[0])
