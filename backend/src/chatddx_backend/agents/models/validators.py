# src/chatddx_backend/agents/models/validators.py
from typing import Any

import jsonref
import jsonschema
from django.core.exceptions import ValidationError


def validate_json_schema(value: dict[str, Any] | None):
    if value is None:
        return
    try:
        jsonschema.Draft7Validator.check_schema(value)

        jsonref.replace_refs(value)  # type: ignore[no-untyped-call]
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid JSON Schema: {e.message}")
    except jsonref.JsonRefError as e:
        raise ValidationError(f"Invalid JSON Reference: {e.message}")
