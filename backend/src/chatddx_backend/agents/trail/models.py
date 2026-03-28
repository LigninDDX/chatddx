# src/chatddx_backend/agents/trail/models.py
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Awaitable, Self, override

from asgiref.sync import sync_to_async
from django.contrib.postgres.fields.array import ArrayField
from django.db import DatabaseError, connection
from django.db.models import (
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    Index,
    Manager,
    Model,
    OneToOneField,
)
from django.utils import timezone
from ninja import Schema as NinjaSchema
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    TypedArrayField = ArrayField[list[int]]
else:
    TypedArrayField = ArrayField


class TrailSchema(BaseModel):
    name: str


class TrailSpec(NinjaSchema):
    id: int
    name: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrailQS(Manager[Any]):
    def get_queryset(self):
        return super().get_queryset().order_by("name", "-updated_at").distinct("name")


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
    created_at = DateTimeField(
        auto_now_add=True,
    )
    updated_at = DateTimeField(
        auto_now=True,
    )

    # objects = TrailQS()

    related_model: Self

    class Meta:
        abstract = True
        ordering = ["-updated_at"]
        get_latest_by = "updated_at"
        unique_together = (("name", "fingerprint"),)
        indexes = [
            Index(
                fields=[
                    "name",
                    "-updated_at",
                ]
            ),
        ]

    async def apply(self) -> int:
        ignore_fields = {"id", "name", "created_at", "updated_at", "fingerprint"}

        db_values: list[Any] = []
        hash_values: list[Any] = []

        db_fields: list[str] = []
        jsonb_args: list[str] = []

        self.updated_at = self.created_at = timezone.now()

        for field in self._meta.concrete_fields:
            if field.primary_key:
                continue

            value = field.get_db_prep_save(getattr(self, field.attname), connection)

            if field.name not in ignore_fields:
                hash_values.append(value)
                jsonb_args.append(f"'{field.column}'")

                if isinstance(field, DecimalField):
                    jsonb_args.append(
                        f"%s::numeric({field.max_digits}, {field.decimal_places})"
                    )
                else:
                    jsonb_args.append("%s")

            if field.name != "fingerprint":
                db_fields.append(field.column)
                db_values.append(value)

        qn = connection.ops.quote_name

        sql = f"""
            INSERT INTO {qn(self._meta.db_table)} ({", ".join(qn(f) for f in db_fields + ["fingerprint"])})
            VALUES (
            {", ".join(["%s"] * len(db_fields))},
            encode(sha256(convert_to(jsonb_build_object({", ".join(jsonb_args)})::text, 'UTF8')), 'hex')
            )
            ON CONFLICT (name, fingerprint)
            DO UPDATE SET updated_at = EXCLUDED.updated_at
            RETURNING id, fingerprint, created_at, (xmax = 0) AS is_created;
        """

        def _fetchone(sql: str, values: list[str]) -> int:
            with connection.cursor() as cursor:
                cursor.execute(sql, values)
                result = cursor.fetchone()
                if not result:
                    raise DatabaseError(
                        "Upsert failed: No rows returned from Postgres."
                    )
                return result[0]

        pk = await sync_to_async(_fetchone)(sql, db_values + hash_values)
        return pk

    @override
    def __str__(self):
        return self.name


async def resolve_related_array_fields(instance: TrailModel):
    tasks: list[Awaitable[Any]] = []

    async def fetch_and_set_array(field: RelatedArrayField, value: Any):
        if not value:
            setattr(instance, field.name, [])
            return

        queryset = field.related_model.objects.filter(pk__in=value)
        resolved_value = [obj async for obj in queryset]

        await asyncio.gather(
            *(resolve_related_array_fields(obj) for obj in resolved_value)
        )

        setattr(instance, field.name, resolved_value)

    for field in instance._meta.concrete_fields:
        if isinstance(field, RelatedArrayField):
            value = getattr(instance, field.name)
            tasks.append(fetch_and_set_array(field, value))

        elif isinstance(field, (ForeignKey, OneToOneField)):
            related_instance = getattr(instance, field.name, None)
            if related_instance is not None:
                tasks.append(resolve_related_array_fields(related_instance))

    if tasks:
        await asyncio.gather(*tasks)

    return instance


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
