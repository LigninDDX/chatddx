# src/chatddx_backend/agents/utils.py
from dataclasses import dataclass
from typing import (
    Generic,
    TypeVar,
    cast,
)

T = TypeVar("T")


@dataclass
class OneOf(Generic[T]):
    value: T


@dataclass
class ListOf(Generic[T]):
    values: list[T]


def one_or_list_of(t: type[T], value: object) -> OneOf[T] | ListOf[T] | None:
    if isinstance(value, t):
        return OneOf(value)

    if isinstance(value, list):
        if not value or all(isinstance(x, t) for x in value):  # type: ignore
            return ListOf(cast(list[T], value))
