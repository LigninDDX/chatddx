import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Any

import orjson
from ninja import Schema as NinjaSchema
from pydantic import BaseModel, ConfigDict, computed_field


def orjson_default(obj: Any):
    match obj:
        case Decimal():
            return str(obj)
        case _:
            raise TypeError(f"Unsupported type: {type(obj)}")


class TrailSchema(BaseModel):
    name: str

    @computed_field
    @property
    def fingerprint(self) -> str:
        serialized = self.model_dump(
            exclude={"name", "fingerprint"},
        )
        json = orjson.dumps(
            serialized,
            option=orjson.OPT_SORT_KEYS,
            default=orjson_default,
        )
        return hashlib.sha256(json).hexdigest()


class TrailSpec(NinjaSchema):
    id: int
    name: str
    fingerprint: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
