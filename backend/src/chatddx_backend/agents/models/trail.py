# src/chatddx_backend/agents/models/trail.py
from __future__ import annotations

from typing import Any, Self, override

from django.contrib.postgres.fields.array import ArrayField
from django.db import DatabaseError, connection
from django.db.models import (
    CharField,
    DateTimeField,
    DecimalField,
    Index,
    Manager,
    Model,
)
from django.utils import timezone

from chatddx_backend.agents.schema import TrailSchema, TrailSpec


class TrailQS(Manager[Any]):
    def get_queryset(self):
        return super().get_queryset().order_by("name", "-updated_at").distinct("name")


class TrailModel(Model):
    Schema: type[TrailSchema]
    Spec: type[TrailSpec]

    name = CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier for this record, last update is considered canon.",
    )
    fingerprint = CharField(
        max_length=64,
        db_index=True,
        help_text="Fingerprint for this configuration",
    )
    created_at = DateTimeField(
        auto_now_add=True,
    )
    updated_at = DateTimeField(
        auto_now=True,
    )

    objects = TrailQS()

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

    @classmethod
    def apply(cls, **kwargs: Any) -> Self:
        return cls.objects.get(
            pk=cls(**kwargs)._apply(),
        )

    def _apply(self) -> int:
        ignore_fields = {"id", "name", "created_at", "updated_at", "fingerprint"}

        db_fields: list[str] = []
        db_values: list[Any] = []

        hash_values: list[Any] = []
        jsonb_args: list[str] = []

        now = timezone.now()
        self.updated_at = now
        self.created_at = now

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
        table_name = qn(self._meta.db_table)

        jsonb_expr = f"jsonb_build_object({', '.join(jsonb_args)})"

        fingerprint_expr = (
            f"encode(sha256(convert_to({jsonb_expr}::text, 'UTF8')), 'hex')"
        )

        all_insert_cols = db_fields + ["fingerprint"]
        field_names = ", ".join(qn(f) for f in all_insert_cols)

        placeholders_list = ["%s"] * len(db_fields)
        placeholders_list.append(fingerprint_expr)
        placeholders = ", ".join(placeholders_list)

        final_values = db_values + hash_values

        conflict_target = qn("name") + ", " + qn("fingerprint")
        update_col = qn("updated_at")

        sql = f"""
            INSERT INTO {table_name} ({field_names})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_target})
            DO UPDATE SET {update_col} = EXCLUDED.{update_col}
            RETURNING id, fingerprint, created_at, (xmax = 0) AS is_created;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, final_values)
            result = cursor.fetchone()

            if not result:
                raise DatabaseError("Upsert failed: No rows returned from Postgres.")

        return result[0]

    @override
    def __str__(self):
        return self.name


class RelatedArrayField(ArrayField):  # type: ignore
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        return super().__new__(cls)  # type: ignore

    def __init__(
        self,
        *args: Any,
        related_model: type[TrailModel],
        **kwargs: Any,
    ) -> None:
        self.related_model: type[TrailModel] = related_model
        super().__init__(*args, **kwargs)

    def get_db_prep_value(self, value: Any, connection: Any, prepared: Any) -> Any:
        if value is not None:
            value = sorted([v.id for v in value])
        return super().get_db_prep_value(value, connection, prepared)

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return value
        return self.related_model.objects.filter(pk__in=value)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["related_model"] = self.related_model
        return name, path, args, kwargs
