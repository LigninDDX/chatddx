# src/chatddx/django/repo/trail/models.py
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, override

from django.contrib.postgres.fields.array import ArrayField
from django.db.models import (
    CharField,
    DateTimeField,
    ForeignKey,
    Model,
    OneToOneField,
)

if TYPE_CHECKING:
    TypedArrayField = ArrayField[list[int]]
else:
    TypedArrayField = ArrayField


class TrailModel(Model):
    fingerprint = CharField(
        max_length=64,
        db_index=True,
        editable=False,
        unique=True,
    )
    timestamp = DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        abstract = True

    @override
    def __str__(self):
        name = getattr(self, "branch_name", None)
        short_hash = self.fingerprint[:6]
        return f"{name} ({short_hash})" if name else short_hash


async def resolve_related_array_fields(model: TrailModel):
    tasks: list[Awaitable[Any]] = []

    async def fetch_and_set_array(field: RelatedArrayField, value: Any):
        if not value:
            setattr(model, field.name, [])
            return

        assert field.associated_model
        queryset = field.associated_model.objects.filter(pk__in=value)
        resolved_value = [obj async for obj in queryset]

        await asyncio.gather(
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
        await asyncio.gather(*tasks)

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
                resolve_related_array_fields_sync(obj)

            setattr(model, field.name, resolved_value)

        elif isinstance(field, (ForeignKey, OneToOneField)):
            associated_model = getattr(model, field.name, None)
            if associated_model is not None:
                resolve_related_array_fields_sync(associated_model)

    return model


class RelatedArrayField(TypedArrayField):
    def __init__(
        self,
        *args: Any,
        associated_model: type[TrailModel],
        **kwargs: Any,
    ) -> None:
        self.associated_model: type[TrailModel] = associated_model
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["associated_model"] = self.associated_model
        return name, path, args, kwargs
