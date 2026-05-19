# src/chatddx/backend/django/main.py
from typing import Any, cast

from chatddx.registry.schemas import TrailRegistry
from chatddx.repo.base import TrailModel, TrailSchema, TrailSpec
from chatddx.repo.form_data import ToolFormData
from chatddx.repo.loaders.trail import model_from_schema, spec_from_model
from chatddx.repo.main import Repo
from chatddx.repo.trail_models import ToolTrailModel
from chatddx.repo.trail_specs import AgentSpec


async def spec_from_registry[T: TrailSpec](
    Spec: type[T],
    name: str,
    registry: TrailRegistry,
) -> T:
    Model = Repo(Spec, TrailModel)
    Schema = Repo(Spec, TrailSchema)

    schema = registry.get_by_type(Schema, name)
    model = await model_from_schema(Model, schema)
    spec = spec_from_model(Spec, model)

    return spec


async def get_agent(name: str, registry: TrailRegistry) -> AgentSpec:
    spec = await spec_from_registry(AgentSpec, name, registry)
    return spec


def resolve_tools(v: Any) -> list[ToolFormData]:
    if isinstance(v, list):
        v = cast(list[Any], v)

        if all(isinstance(x, ToolFormData) for x in v):
            return cast(list[ToolFormData], v)

        if all(isinstance(x, int) for x in v):
            return [
                ToolFormData.model_validate(tool_model)
                for tool_model in ToolTrailModel.objects.filter(pk__in=v)
            ]

    raise ValueError(f"unexpected value {v}")
