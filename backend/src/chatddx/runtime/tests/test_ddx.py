# src/chatddx/backend/repo/test/test_ddx.py
import json
from pathlib import Path

import pytest
import pytest_asyncio

from chatddx.core.models import IdentityModel
from chatddx.repo.branch_spec import AgentBranchSpec
from chatddx.repo.shufflers.main import dump_trail_registry_async, load_branch_async
from chatddx.runtime.runners import run_from_spec


@pytest_asyncio.fixture(autouse=True)
async def dump_registry(owner: IdentityModel):
    path = Path(__file__).parent / "data/ddx-management.toml"
    return await dump_trail_registry_async(path, owner_name=owner.name)


@pytest_asyncio.fixture
async def owner():
    owner, _created = await IdentityModel.objects.aget_or_create(name="alex")
    return owner


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_ddx_management(owner: IdentityModel):
    data_path = Path(__file__).parent / "data/cases/case_a.txt"
    expects_path = Path(__file__).parent / "data/expects/case_a.json"

    with data_path.open("r") as f:
        case_a = f.read()

    with expects_path.open("r") as f:
        data = json.load(f)

    spec = await load_branch_async(
        "agent",
        "ddx-management",
        owner.name,
        as_schema=AgentBranchSpec,
    )
    result = await run_from_spec(spec.target, case_a)

    print(json.dumps(result.output, indent=2))
    assert result.output == data
