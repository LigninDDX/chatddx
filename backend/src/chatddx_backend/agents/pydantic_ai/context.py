from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic_ai import StructuredDict

from chatddx_backend.agents.schemas import AgentSpec, SessionSpec

OutputType = bool | int | str | Decimal | list[Any] | dict[str, Any]


def jsonschema_to_type(jsonschema: dict[str, Any]) -> type[OutputType]:
    match jsonschema.get("type"):
        case "bool":
            return bool
        case "integer":
            return int
        case "number":
            return Decimal
        case "array":
            return list
        case "object":
            return StructuredDict(jsonschema)
        case _:
            invalid_type = jsonschema.get("type")
            raise ValueError(f"Unexpected output type '{invalid_type}'")


@dataclass(frozen=True)
class AgentContext:
    agent: AgentSpec
    output_type: type[OutputType] | None = None
    session: SessionSpec | None = None
