# src/chatddx_backend/agents/trail/schema.py
import hashlib
from datetime import datetime

import orjson
from ninja import Schema as NinjaSchema
from pydantic import BaseModel, computed_field

from chatddx_backend.agents.utils import default_parser


class TrailSchema(BaseModel):
    name: str

    @computed_field
    def fingerprint(self) -> str:
        serialized = self.model_dump(
            exclude={"name", "fingerprint"},
        )
        json = orjson.dumps(
            serialized,
            option=orjson.OPT_SORT_KEYS,
            default=default_parser,
        )
        return hashlib.sha256(json).hexdigest()


class TrailSpec(NinjaSchema):
    id: int
    name: str
    fingerprint: str
    timestamp: datetime
