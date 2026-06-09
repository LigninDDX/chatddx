# src/chatddx/backend/repo/test/test_shufflers.py
from pathlib import Path

import pytest
import pytest_asyncio

from chatddx.core.models import IdentityModel
from chatddx.history.session import resume_session, start_session
from chatddx.repo.shufflers.main import (
    dump_trail_registry_async,
    load_agents,
    load_agents_async,
    load_branch_async,
)
from chatddx.runtime.runners import run_from_session, run_from_spec
from chatddx.utils import Dispatcher


@pytest_asyncio.fixture(autouse=True)
async def dump_registry(owner: IdentityModel):
    path = Path(__file__).parent / "data/test-registry.toml"
    return await dump_trail_registry_async(path, owner_name=owner.name)


dispatcher = Dispatcher()


@pytest_asyncio.fixture
async def owner():
    owner, _created = await IdentityModel.objects.aget_or_create(name="alex")
    return owner


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_swift_list(owner: IdentityModel):
    agents = await load_agents_async(
        owner_name=owner.name,
        output_type="swift",
    )

    assert len(agents) == 1
