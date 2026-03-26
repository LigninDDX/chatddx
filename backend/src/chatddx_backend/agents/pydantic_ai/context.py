from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from pydantic_ai import ModelMessage, StructuredDict

from chatddx_backend.agents.models import ValidationStrategy
from chatddx_backend.agents.schemas import AgentSpec

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
    spec: AgentSpec
    output_type: type[OutputType] | None
    output_schema: dict[str, Any] | None
    validation_strategy: ValidationStrategy
    message_history: Sequence[ModelMessage] | None = None
