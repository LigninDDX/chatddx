from typing import TypeVar

from chatddx_backend.agents import type_map
from chatddx_backend.agents.schemas import AgentSpec, TrailRegistry
from chatddx_backend.agents.trail import (
    TrailModel,
    TrailSchema,
    TrailSpec,
    model_from_schema,
    spec_from_model,
)

T = TypeVar("T", bound=TrailSpec)


async def spec_from_registry(
    Spec: type[T],
    name: str,
    registry: TrailRegistry,
) -> T:
    Model = type_map.resolve(Spec, TrailModel)
    Schema = type_map.resolve(Spec, TrailSchema)

    schema = registry.get(Schema, name)
    model = await model_from_schema(Model, schema)
    spec = spec_from_model(Spec, model)

    return spec


async def agent_spec(name: str, registry: TrailRegistry) -> AgentSpec:
    spec = await spec_from_registry(AgentSpec, name, registry)
    return spec
