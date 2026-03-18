# src/chatddx_backend/agents/models/trail.py
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Self, override

import tomli
from django.contrib.postgres.fields.array import ArrayField
from django.db import DatabaseError, IntegrityError, connection
from django.db.models import (
    CharField,
    DateTimeField,
    DecimalField,
    Field,
    Index,
    Manager,
    Model,
)
from django.utils import timezone

from chatddx_backend.agents.utils import camel_to_snake

type TrailRelation = TrailModel | int | str | dict[str, Any]


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
    def record_name(cls) -> str:
        return camel_to_snake(cls.__name__)

    @classmethod
    def upsert(cls, **kwargs: Any) -> Self:
        concrete_data = {}

        for key, value in kwargs.items():
            concrete_data[key] = value

        return cls.objects.get(
            pk=cls(**concrete_data).resolve(),
        )

    def resolve(self) -> Self:
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

        fingerprint_expr = f"encode(sha256(CAST({jsonb_expr} AS text)::bytea), 'hex')"

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


class RelatedArrayField(ArrayField):  # type: ignore[type-arg]
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        return super().__new__(cls)  # type: ignore[call-overload]

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


def serialize(
    instance: TrailModel,
    target_type: type[TrailRelation],
) -> dict[str, Any]:
    return {
        field.name: serialize_field(
            instance,
            field,
            target_type,
        )
        for field in instance._meta.concrete_fields
    }


def serialize_field(
    instance: TrailModel,
    field: Field[Any, Any],
    target_type: type[TrailRelation],
) -> Any:
    value = getattr(instance, field.name)

    if isinstance(field, RelatedArrayField):
        return serialize_array_field(
            value,
            target_type,
            field.related_model,
        )

    if isinstance(value, TrailModel):
        return serialize_relation_field(
            value,
            target_type,
        )

    return value


def serialize_array_field(
    values: list[TrailRelation],
    target_type: type[TrailRelation],
    model: type[TrailModel],
) -> list[TrailRelation]:
    if not values or isinstance(values[0], target_type):
        return values

    match values[0]:
        case int():
            qs = model.objects.filter(pk__in=values)
        case str():
            qs = model.objects.filter(name__in=values)
        case dict():
            qs = model.objects.filter(pk__in=[v["id"] for v in values])
        case TrailModel():
            qs = values

    return [serialize_relation_field(item, target_type, model) for item in qs]


def serialize_relation_field(
    value: TrailRelation,
    target_type: type[TrailRelation],
    model: type[TrailModel] | None = None,
) -> TrailRelation:

    if isinstance(value, target_type):
        return value

    match value:
        case int():
            assert model
            value = model.objects.get(pk=value)
        case str():
            assert model
            value = model.objects.get(name=value)
        case dict():
            assert model
            value = model.objects.get(pk=value["id"])
        case TrailModel():
            pass

    if target_type == int:
        return value.pk
    elif target_type == str:
        return value.name
    elif target_type == dict:
        return serialize(value, dict)

    return value


@dataclass
class TrailManager:
    library: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrailManager:
        return cls(library=deepcopy(data))

    @classmethod
    def from_toml(cls, path: Path) -> TrailManager:
        with path.open("rb") as f:
            return cls(library=tomli.load(f))

    def _get_values(self, cls: type[TrailModel], name: str) -> dict[str, Any]:
        record_name = cls.record_name()
        model_data = self.library.get(record_name, {})

        if name not in model_data:
            raise ValueError(f"'{name}' not found in {record_name}")

        return self.library[record_name][name].copy()

    def deref(self, Model: type[TrailModel], record_name: str) -> dict[str, Any]:
        record = self.library[Model.record_name()][record_name].copy()
        result: dict[str, Any] = {}

        for field in Model._meta.concrete_fields:
            if not field.name in record:
                continue

            result[field.name] = record[field.name]

            if field.many_to_one or field.one_to_one:
                result[field.name] = self.deref(
                    field.related_model, record[field.name]
                ) | {"name": record[field.name]}

            if isinstance(field, DecimalField):
                result[field.name] = Decimal(str(record[field.name]))

            if isinstance(field, RelatedArrayField):
                result[field.name] = [
                    self.deref(field.related_model, item) | {"name": item}
                    for item in record[field.name]
                ]

        return result

    def get_instance(
        self,
        cls: type[TrailModel],
        *args: str,
        **kwargs: Any,
    ) -> TrailModel:
        name = kwargs.get("name", args[0])

        if args[0] != name:
            raise ValueError(
                f"the first argument ({args[0]}) must match keyword argument 'name' ({name}) if both are defined"
            )

        values = self._get_values(cls, name) | kwargs | {"name": name}

        for field in cls._meta.concrete_fields:
            if isinstance(field, RelatedArrayField):
                values[field.name] = self.resolve_array_field(field, values[field.name])
            if field.many_to_one or field.one_to_one:
                values[field.name] = self.resolve_relation(field, values[field.name])

        return cls.upsert(**values)  # type: ignore

    def resolve_array_field(
        self,
        field: RelatedArrayField,
        values: list[TrailRelation],
    ) -> list[int]:
        new_values: list[int] = []
        for item in values:
            match item:
                case int():
                    new_values.append(item)
                case str():
                    new_values.append(self.get_instance(field.related_model, item).pk)
                case dict():
                    new_values.append(item["id"])
                case TrailModel():
                    if not item.pk:
                        item.pk = item.resolve()
                    new_values.append(item.pk)

        found = field.related_model.objects.filter(pk__in=new_values).values_list(
            "pk", flat=True
        )

        missing = set(new_values) - set(found)
        if missing:
            raise IntegrityError(
                f"Invalid {field.related_model.__name__} pk(s): {missing}"
            )

        return sorted(new_values)

    def resolve_relation(
        self,
        field: Field[Any, Any],
        value: TrailRelation,
    ) -> TrailModel:
        assert field.related_model
        match value:
            case str():
                return self.get_instance(field.related_model, value)
            case int():
                return field.related_model.objects.get(pk=value)
            case dict():
                return field.related_model.objects.get(pk=value["id"])
            case TrailModel():
                return value
