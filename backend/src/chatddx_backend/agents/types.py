from dataclasses import dataclass
from typing import Any

from chatddx_backend.agents.models import Agent


@dataclass(frozen=True)
class AgentDeps:
    schema: dict[str, Any] | None
    validation_strategy: Agent.ValidationStrategy
