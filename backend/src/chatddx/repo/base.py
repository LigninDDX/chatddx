from __future__ import annotations

from datetime import datetime
from typing import Any, override

from django.db.models import (
    PROTECT,
    CharField,
    DateTimeField,
    ForeignKey,
    Index,
    Manager,
)
from django.db.models import Field as DjangoField
from django.db.models import Model as DjangoModel
from django.forms import model_to_dict
from ninja import Schema as NinjaSchema
from pydantic import (
    BaseModel,
    PrivateAttr,
    ValidationInfo,
    computed_field,
    model_validator,
)

from chatddx.core.fields import CoercedStr, NullableStr
from chatddx.core.models import IdentityModel
from chatddx.registry.schemas import RegistryInstance
from chatddx.utils import generate_fingerprint


class BranchProxy:
    pk: int
    name: str
    objects: Manager[BranchModel]
    target: TrailModel

    @override
    def __str__(self) -> str:
        return self.name


class BranchBase(BaseModel):
    owner_id: int
    name: str
    timestamp: datetime | None = None


class TrailSchema(RegistryInstance):
    _name: str | None = PrivateAttr()

    @computed_field
    def fingerprint(self) -> str:
        return self.as_fingerprint()

    def as_fingerprint(self):
        serialized = self.model_dump(exclude={"fingerprint"})
        return generate_fingerprint(serialized)


class TrailSchemaRef(BaseModel):
    fingerprint: str


class BranchSchema[T: TrailSchema](BranchBase):
    target_type: type[T]
    target_id: int


class BranchModel(DjangoModel):
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    name = CharField(max_length=255)
    timestamp = DateTimeField(
        auto_now_add=True,
    )
    target: DjangoField[Any, Any]

    class Meta:
        abstract = True
        indexes = [
            Index(fields=["owner", "name", "-timestamp"]),
        ]

    def as_proxy(self, proxy_model: type[BranchProxy]):
        return proxy_model.from_db(
            db=self._state.db,
            field_names=[f.name for f in self._meta.fields],
            values=[getattr(self, f.name) for f in self._meta.fields],
        )


class TrailSpec(NinjaSchema):
    id: int
    fingerprint: str
    timestamp: datetime


class BranchSpec[T: TrailSpec](BranchBase, NinjaSchema):
    id: int
    target: T


class BaseFormDataIn(NinjaSchema):
    name: NullableStr = None

    @model_validator(mode="before")
    def merge_target(v: Any):
        if hasattr(v, "target"):
            branch = model_to_dict(v)
            trail = model_to_dict(v.target)

            return branch | trail

        return v


class BaseFormDataOut(NinjaSchema):
    id: CoercedStr
    name: str = ""

    @model_validator(mode="after")
    def add_name_from_context(self, info: ValidationInfo):
        if info.context:
            self.name = info.context.get("name")
        return self


class TrailModel(DjangoModel):
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
