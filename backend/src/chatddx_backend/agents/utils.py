# src/chatddx_backend/agents/utils.py
import asyncio
import inspect
from dataclasses import dataclass
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    TypeVar,
    cast,
    get_type_hints,
)

from pydantic import HttpUrl

T = TypeVar("T")

Observer = Callable[[T], None | Awaitable[None]]


@dataclass
class OneOf(Generic[T]):
    value: T


@dataclass
class ListOf(Generic[T]):
    values: list[T]


def default_parser(obj: Any):
    match obj:
        case Decimal():
            return str(obj)
        case HttpUrl():
            return str(obj)
        case _:
            raise TypeError(f"Unsupported type: {type(obj)}")


def one_or_list_of(t: type[T], value: object) -> OneOf[T] | ListOf[T] | None:
    if isinstance(value, t):
        return OneOf(value)

    if isinstance(value, list):
        if not value or all(isinstance(x, t) for x in value):  # type: ignore
            return ListOf(cast(list[T], value))


class Dispatcher:
    def __init__(self):
        self._handlers: dict[type[Any], list[Observer[Any]]] = {}

    def subscribe(self, fn: Observer[T]) -> Observer[T]:
        target = fn if inspect.isroutine(fn) else fn.__call__

        hints = get_type_hints(target)
        sig = inspect.signature(target)
        params = list(sig.parameters.values())

        name = getattr(fn, "__name__", type(fn).__name__)
        if not params:
            raise ValueError(f"Handler {name} must accept an argument.")

        first_arg_name = params[0].name
        item_type = hints.get(first_arg_name)

        if not item_type:
            raise TypeError(
                f"Missing type hint for '{first_arg_name}' in {fn.__name__}"
            )

        self._handlers.setdefault(item_type, []).append(fn)
        return fn

    async def publish(self, data: Any):
        tasks: list[Awaitable[Any]] = []
        for registered_type, handlers in self._handlers.items():
            if registered_type == Any or isinstance(data, registered_type):
                for handler in handlers:
                    if inspect.iscoroutinefunction(handler):
                        tasks.append(handler(data))
                    else:
                        tasks.append(asyncio.to_thread(handler, data))
        await asyncio.gather(*tasks)
