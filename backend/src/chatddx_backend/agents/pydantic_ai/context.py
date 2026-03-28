from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chatddx_backend.agents.schemas import AgentSpec, SessionSpec

OutputType = bool | int | str | Decimal | list[Any] | dict[str, Any]


@dataclass(frozen=True)
class AgentContext:
    agent: AgentSpec
    output_type: type[OutputType] | None = None
    session: SessionSpec | None = None
