# src/chatddx/backend/django/main.py
from chatddx.repo.base import TrailModel, TrailSpec
from chatddx.repo.loaders.trail import model_from_schema, spec_from_model
from chatddx.repo.main import BundleName, Repo
from chatddx.repo.trail_schemas import TrailRegistry
from chatddx.repo.trail_specs import AgentSpec


async def spec_from_registry[T: TrailSpec](
    bundle: BundleName,
    name: str,
    registry: TrailRegistry,
) -> TrailSpec:
    Model = Repo(bundle, TrailModel)
    Spec = Repo(bundle, TrailSpec)

    schema = getattr(registry, bundle)[name]
    model = await model_from_schema(Model, schema)
    spec = spec_from_model(Spec, model)

    return spec


async def get_agent(name: str, registry: TrailRegistry) -> AgentSpec:
    spec = await spec_from_registry("agent", name, registry)
    return spec
