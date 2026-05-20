import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

PRECISION = Decimal("0.01")


class SamplingDecimal(Decimal):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, v: Any) -> "SamplingDecimal":
        return cls(Decimal(str(v)).quantize(PRECISION, rounding=ROUND_HALF_UP))


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class DecimalDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(parse_float=Decimal, *args, **kwargs)
