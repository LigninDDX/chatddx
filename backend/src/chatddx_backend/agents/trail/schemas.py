from datetime import datetime

from ninja import Schema as NinjaSchema
from pydantic import BaseModel, ConfigDict


class TrailSchema(BaseModel):
    name: str


class TrailSpec(NinjaSchema):
    id: int
    name: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
