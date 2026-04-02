from dataclasses import dataclass, field
from typing import cast

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet
from pydantic import TypeAdapter

from chatddx_backend.agents.trail import TrailModel, TrailSpec, spec_from_model
from chatddx_backend.agents.trail.models import resolve_related_array_fields_sync


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


def serialize_trail(Spec: type[TrailSpec], qs):
    return TypeAdapter(dict[str, Spec]).dump_json(
        {
            str(model.pk): spec_from_model(
                Spec,
                resolve_related_array_fields_sync(cast(TrailModel, model)),
            )
            for model in qs
        }
    )
