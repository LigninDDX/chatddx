from __future__ import annotations

from datetime import datetime
from typing import Any, override

from django.db.models import (
    PROTECT,
    CharField,
    DateTimeField,
    Field,
    ForeignKey,
    Index,
    Model,
)
from ninja import Schema as NinjaSchema
from pydantic import (
    BaseModel,
    ValidationInfo,
    computed_field,
    model_validator,
)

from chatddx.core.models import IdentityModel
from chatddx.utils import generate_fingerprint


class BranchBase(BaseModel):
    owner_id: int
    name: str
    timestamp: datetime | None = None


class TrailSchema(BaseModel):
    @computed_field
    def fingerprint(self) -> str:
        return self.as_fingerprint()

    def as_fingerprint(self):
        serialized = self.model_dump(exclude={"fingerprint"})
        return generate_fingerprint(serialized)


class TrailSchemaRef(BaseModel):
    fingerprint: str

    @classmethod
    def from_schema(cls, schema: TrailSchema):
        return cls.model_validate(schema.model_dump())


class BranchSchema[T: TrailSchema](BranchBase):
    target_type: type[T]
    target_id: int


class BranchModel(Model):
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    name = CharField(max_length=255)
    timestamp = DateTimeField(
        auto_now_add=True,
    )
    target: Field[Any, Any]

    class Meta:
        abstract = True
        indexes = [
            Index(fields=["owner", "name", "-timestamp"]),
        ]


class TrailSpec(NinjaSchema):
    id: int
    fingerprint: str
    timestamp: datetime


class BranchSpec[T: TrailSpec](BranchBase, NinjaSchema):
    id: int
    target: T


class BaseFormDataIn(NinjaSchema):
    name: str | None = None

    @model_validator(mode="after")
    def add_name_from_context(self, info: ValidationInfo):
        if info.context:
            self.name = info.context.get("name")
        return self


class BaseFormDataOut(NinjaSchema):
    name: str | None = None

    @model_validator(mode="after")
    def add_name_from_context(self, info: ValidationInfo):
        if info.context:
            self.name = info.context.get("name")
        return self


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
