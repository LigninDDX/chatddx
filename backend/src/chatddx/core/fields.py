import tomllib
from typing import Annotated, Any

import tomli_w
from pydantic import BeforeValidator, JsonValue, PlainSerializer


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


def dict_to_toml(v: dict[str, Any] | None) -> str:
    return tomli_w.dumps(v).strip() if v is not None else ""


def list_to_text(v: list[str] | None) -> str:
    return "\n".join(v) if v is not None else ""


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
