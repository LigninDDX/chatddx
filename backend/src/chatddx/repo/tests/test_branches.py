# src/chatddx/backend/repo/test/test_branches.py
from pathlib import Path

import pytest
import pytest_asyncio

from chatddx.core.models import IdentityModel
from chatddx.registry.schemas import TrailRegistry
from chatddx.repo.base import BranchSchema, TrailSchema
from chatddx.repo.loaders.branches import get_branch_model_async, get_branch_schema
from chatddx.repo.trail_schemas import AgentSchema, ConnectionSchema


async def get_branches_from_registry(owner: IdentityModel, registry: TrailRegistry):
    branches: dict[str, BranchSchema[TrailSchema]] = {}
    for _, registry_dict in registry:
        for name, schema in registry_dict.items():
            branches[name] = await get_branch_schema(
                name=name,
                owner_id=owner.pk,
                trail_schema=schema,
            )
    return branches


@pytest.fixture
def registry():
    return TrailRegistry.from_file(Path(__file__).parent / "data/test-registry.toml")


@pytest_asyncio.fixture
async def owner():
    owner, _created = await IdentityModel.objects.aget_or_create(name="alex")
    return owner


@pytest_asyncio.fixture
async def branches(owner: IdentityModel, registry: TrailRegistry):
    return await get_branches_from_registry(owner, registry)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_schemas_from_registry(branches: dict[str, BranchSchema[TrailSchema]]):
    assert branches["agent-1"].name == "agent-1"
    assert branches["agent-1"].target_type == AgentSchema

    assert branches["connection-1"].name == "connection-1"
    assert branches["connection-1"].target_type == ConnectionSchema


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_model_from_schema(owner: IdentityModel, registry: TrailRegistry):
    branch_model = await get_branch_model_async(
        "agent-1", owner.pk, registry.agent["agent-1"]
    )
    assert branch_model.pk is not None
    assert branch_model.name == "agent-1"
