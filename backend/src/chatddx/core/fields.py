import tomllib
from typing import Annotated, Any

import jsonschema
import tomli_w
from pydantic import BeforeValidator, JsonValue, PlainSerializer


def validate_json_schema(v: Any) -> Any:
    if v is not None:
        try:
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}")
        check_v = tomllib.loads(tomli_w.dumps(v))
        assert check_v == v
    return v


def parse_toml_or_dict(v: Any) -> Any:
    match v:
        case None:
            return None
        case str():
            if not v.strip():
                return None
            try:
                return tomllib.loads(v)
            except Exception as e:
                raise ValueError(e)
        case dict():
            return v  # pyright: ignore[reportUnknownVariableType]
        case _:
            raise ValueError(f"Unexpected input: {v}")


def parse_text_or_list(v: Any) -> list[str] | None:
    match v:
        case None:
            return None
        case str():
            if not v.strip():
                return None
            return [line.strip() for line in v.splitlines() if line.strip()]
        case list():
            return v  # pyright: ignore[reportUnknownVariableType]
        case _:
            raise ValueError(f"Unexpected input: {v}")


def dict_to_toml(v: Any) -> str:
    match v:
        case dict():
            return tomli_w.dumps(v).strip()
        case str():
            return v
        case None:
            return ""
        case _:
            raise ValueError(f"Unexpected type: {v}")


def list_to_text(v: Any) -> str:
    match v:
        case list():
            return "\n".join(v)
        case str():
            return v
        case None:
            return ""
        case _:
            raise ValueError(f"Unexpected type: {v}")


TomlDict = Annotated[
    dict[str, JsonValue] | None,
    BeforeValidator(parse_toml_or_dict),
    PlainSerializer(
        dict_to_toml,
        return_type=str,
        when_used="json",
    ),
]


TextList = Annotated[
    list[str] | None,
    BeforeValidator(parse_text_or_list),
    PlainSerializer(
        list_to_text,
        return_type=str,
        when_used="json",
    ),
]
