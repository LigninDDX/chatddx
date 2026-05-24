import asyncio
from collections.abc import Awaitable
from typing import Any

from django.db.models import ForeignKey, OneToOneField

from chatddx.core.django_fields import RelatedArrayField
from chatddx.repo.base import TrailModel


async def resolve_related_array_fields(model: TrailModel):
    tasks: list[Awaitable[Any]] = []

    async def fetch_and_set_array(field: RelatedArrayField, value: Any):
        if not value:
            setattr(model, field.name, [])
            return

        assert field.associated_model
        queryset = field.associated_model.objects.filter(pk__in=value)
        resolved_value = [obj async for obj in queryset]

        _ = await asyncio.gather(
            *(resolve_related_array_fields(obj) for obj in resolved_value)
        )

        setattr(model, field.name, resolved_value)

    for field in model._meta.concrete_fields:
        if isinstance(field, RelatedArrayField):
            value = getattr(model, field.name)
            tasks.append(fetch_and_set_array(field, value))

        elif isinstance(field, (ForeignKey, OneToOneField)):
            associated_model = getattr(model, field.name, None)
            if associated_model is not None:
                tasks.append(resolve_related_array_fields(associated_model))

    if tasks:
        _ = await asyncio.gather(*tasks)

    return model


def resolve_related_array_fields_sync(model: TrailModel):
    for field in model._meta.concrete_fields:
        if isinstance(field, RelatedArrayField):
            value = getattr(model, field.name)

            if not value:
                setattr(model, field.name, [])
                continue

            queryset = field.associated_model.objects.filter(pk__in=value)
            resolved_value = list(queryset)

            for obj in resolved_value:
                _ = resolve_related_array_fields_sync(obj)

            setattr(model, field.name, resolved_value)

        elif isinstance(field, (ForeignKey, OneToOneField)):
            associated_model = getattr(model, field.name, None)
            if associated_model is not None:
                _ = resolve_related_array_fields_sync(associated_model)

    return model
