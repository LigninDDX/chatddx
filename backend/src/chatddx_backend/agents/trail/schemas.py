from datetime import datetime
from typing import ClassVar

from ninja import Schema
from pydantic import ConfigDict


class TrailSchema(Schema):
    record_type: ClassVar[str]
    name: str


class TrailSpec(Schema):
    id: int
    name: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
