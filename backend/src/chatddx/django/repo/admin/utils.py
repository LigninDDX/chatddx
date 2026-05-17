from dataclasses import dataclass, field
from typing import Any

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet


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

    result = {}

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
