import json
from decimal import Decimal
from typing import Any


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class DecimalDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(parse_float=Decimal, *args, **kwargs)
