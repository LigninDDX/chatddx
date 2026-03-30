# src/chatddx_backend/agents/trail/models.py
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, override

from django.contrib.postgres.fields.array import ArrayField
from django.db.models import (
    CharField,
    DateTimeField,
    ForeignKey,
    Index,
    Model,
    OneToOneField,
)

if TYPE_CHECKING:
    TypedArrayField = ArrayField[list[int]]
else:
    TypedArrayField = ArrayField


class TrailModel(Model):
    name = CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier for this record, last update is considered canon.",
    )
    fingerprint = CharField(
        max_length=64,
        db_index=True,
        editable=False,
        help_text="Fingerprint for this configuration",
    )
    timestamp = DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        abstract = True
        unique_together = (("name", "fingerprint"),)
        indexes = [Index(fields=["name"])]

    @override
    def __str__(self):
        return self.name


async def resolve_related_array_fields(model: TrailModel):
    tasks: list[Awaitable[Any]] = []

    async def fetch_and_set_array(field: RelatedArrayField, value: Any):
        if not value:
            setattr(model, field.name, [])
            return

        queryset = field.related_model.objects.filter(pk__in=value)
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
            related_model = getattr(model, field.name, None)
            if related_model is not None:
                tasks.append(resolve_related_array_fields(related_model))

    if tasks:
        await asyncio.gather(*tasks)

    return model


class RelatedArrayField(TypedArrayField):
    def __init__(
        self,
        *args: Any,
        related_model: type[TrailModel],
        **kwargs: Any,
    ) -> None:
        self.related_model: type[TrailModel] = related_model
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["related_model"] = self.related_model
        return name, path, args, kwargs
