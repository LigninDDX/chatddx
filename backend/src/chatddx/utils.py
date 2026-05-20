import asyncio
import hashlib
import inspect
from dataclasses import dataclass, field
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

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet
from pydantic import HttpUrl, JsonValue

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


def generate_fingerprint(data: dict[str, JsonValue]):
    import orjson

    json = orjson.dumps(
        data,
        option=orjson.OPT_SORT_KEYS,
        default=default_parser,
    )

    return hashlib.sha256(json).hexdigest()


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


def flatten_dict(d: dict[str, Any]):
    return {
        f"{outer}{inner}": value
        for outer, inner_dict in d.items()
        for inner, value in inner_dict.items()
    }


def unflatten_dict(
    d: dict[str, Any],
    outer_keys: list[str],
) -> dict[str, dict[str, Any]]:

    result: dict[str, Any] = {}

    for flat_key, value in d.items():
        for outer in outer_keys:
            if flat_key.startswith(outer):
                inner = flat_key[len(outer) :].strip("_")

                if outer not in result:
                    result[outer] = {}

                result[outer][inner] = value
                break

    return result


@dataclass
class StepNavItem:
    pk: int | None = None
    text: str | None = None


@dataclass
class StepNav:
    next_: StepNavItem = field(default_factory=StepNavItem)
    prev_: StepNavItem = field(default_factory=StepNavItem)


def get_step_nav(
    model: DjangoModel,
    qs: QuerySet[DjangoModel],
) -> StepNav:

    pks = list(qs.order_by("id").values_list("pk", flat=True))

    step_nav = StepNav()
    pk_index = pks.index(model.pk)

    step_nav.prev_.pk = pks[pk_index - 1] if pk_index > 0 else None
    step_nav.next_.pk = pks[pk_index + 1] if pk_index < len(pks) - 1 else None

    if step_nav.prev_.pk:
        prev_model = qs.get(pk=step_nav.prev_.pk)
        step_nav.prev_.text = str(prev_model)

    if step_nav.next_.pk:
        next_model = qs.get(pk=step_nav.next_.pk)
        step_nav.next_.text = str(next_model)

    return step_nav


def truncate_content(content: str | None, limit: int):
    if content is None:
        return ""
    if len(content) > limit:
        return content[:limit] + " (...)"
    return content
