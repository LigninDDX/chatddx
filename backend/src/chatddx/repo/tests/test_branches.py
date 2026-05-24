# src/chatddx/backend/repo/test/test_branches.py
from pathlib import Path

import pytest
import pytest_asyncio

from chatddx.core.models import IdentityModel
from chatddx.repo.base import BranchModel
from chatddx.repo.branch_spec import AgentBranchSpec
from chatddx.repo.shufflers.main import (
    dump_trail_registry_async,
    ensure_identity_async,
    load_branch_async,
)


@pytest_asyncio.fixture(autouse=True)
async def branches(owner: IdentityModel):
    path = Path(__file__).parent / "data/test-registry.toml"
    return await dump_trail_registry_async(path, owner.name)


@pytest_asyncio.fixture
async def owner():
    return await ensure_identity_async("alex")


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_schemas_from_registry(branches: dict[str, dict[int, BranchModel]]):
    assert len(branches["agent"]) == 4
    assert len(branches["connection"]) == 2


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_model_from_schema(owner: IdentityModel):
    branch_model = await load_branch_async(
        "agent",
        "agent-1",
        owner.name,
        AgentBranchSpec,
    )
    assert branch_model.id is not None
    assert branch_model.name == "agent-1"
