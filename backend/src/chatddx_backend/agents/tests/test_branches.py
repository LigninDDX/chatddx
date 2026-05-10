# chatddx_backend/agents/test/test_branches.py
from pathlib import Path
from typing import TypeVar

import pytest

from chatddx_backend.agents import trail_map
from chatddx_backend.agents.models import IdentityModel
from chatddx_backend.agents.models.history import BranchModel
from chatddx_backend.agents.schemas import (
    AgentSchema,
    BranchSchema,
    TrailRegistry,
)
from chatddx_backend.agents.trail import TrailModel, TrailSchema
from chatddx_backend.agents.trail.spec_loader import pk_from_schema

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-registry.toml"
)


TrailSchemaT = TypeVar("TrailSchemaT", bound=TrailSchema)


async def get_branch_schema(
    name: str,
    owner_id: int,
    trail_schema: TrailSchemaT,
) -> BranchSchema[TrailSchemaT]:
    return BranchSchema[type(trail_schema)](
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


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_schemas_from_registry():
    owner = IdentityModel(name="alex")
    owner.save()

    branch_schemas: list[BranchSchema[TrailSchema]] = [
        await get_branch_schema(
            name=name,
            owner_id=owner.pk,
            trail_schema=schema,
        )
        for _, registry_dict in registry
        for name, schema in registry_dict.items()
    ]

    for branch_schema in branch_schemas:
        branch_model = trail_map.resolve(
            type(branch.target), TrailModel
        ).branches.rel.related_model
        branch_instance = branch_model(**branch.model_dump())
        print(branch_instance)

    assert branches["agent-1"].name == "agent-1"
    assert type(branches["agent-1"].target) == AgentSchema
    assert branches["agent-1"].target.instructions == "hello 1"
