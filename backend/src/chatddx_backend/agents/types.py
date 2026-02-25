from dataclasses import dataclass

from chatddx_backend.agents.models import Agent


@dataclass(frozen=True)
class AgentDeps:
    schema: dict | None
    validation_strategy: Agent.ValidationStrategy
