from typing import TypeVar

from chatddx_backend.agents import trail_map
from chatddx_backend.agents.models.history import BranchModel
from chatddx_backend.agents.schemas import BranchSchema
from chatddx_backend.agents.trail import TrailModel, TrailSchema, pk_from_schema

TrailSchemaT = TypeVar("TrailSchemaT", bound=TrailSchema)


async def get_branch_model(
    name: str,
    owner_id: int,
    trail_schema: TrailSchemaT,
) -> BranchModel:
    branch_schema = await get_branch_schema(name, owner_id, trail_schema)
    branch_model = await model_from_schema(branch_schema)
    return branch_model


async def get_branch_schema(
    name: str,
    owner_id: int,
    trail_schema: TrailSchemaT,
) -> BranchSchema[TrailSchemaT]:
    return BranchSchema[TrailSchemaT](
        name=name,
        owner_id=owner_id,
        target_type=type(trail_schema),
        target_id=await pk_from_schema(
            trail_map.resolve(
                type(trail_schema),
                TrailModel,
            ),
            trail_schema,
        ),
    )


async def model_from_schema(
    schema: BranchSchema[TrailSchemaT],
) -> BranchModel:
    trail_model_class = trail_map.resolve(schema.target_type, TrailModel)
    branch_model_class = trail_model_class.branches.rel.related_model  # type: ignore[attr-defined]
    instance, _ = await branch_model_class.objects.aget_or_create(
        owner_id=schema.owner_id,
        name=schema.name,
        target_id=schema.target_id,
    )
    return instance
