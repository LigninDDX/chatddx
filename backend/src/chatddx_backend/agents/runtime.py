from typing import Any

from chatddx_backend.agents.models import Agent
from chatddx_backend.agents.schemas import AgentSchema
from chatddx_backend.agents.specs import AgentSpec
from chatddx_backend.agents.trail import (
    model_from_schema,
    schema_from_registry,
    spec_from_model,
)


async def agent_spec(name: str, registry: dict[str, Any]) -> AgentSpec:
    schema = schema_from_registry(AgentSchema, name, registry)
    model = await model_from_schema(Agent, schema)
    spec = spec_from_model(AgentSpec, model)
    return spec
