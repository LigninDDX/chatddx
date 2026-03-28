from pathlib import Path

import pytest
import tomli
from django.contrib.auth.models import User as AuthUser

from chatddx_backend.agents.main import get_agent
from chatddx_backend.agents.models.session import User
from chatddx_backend.agents.pydantic_ai.runners import run_from_session
from chatddx_backend.agents.schemas import TrailRegistry
from chatddx_backend.agents.session import get_user, resume_session, start_session

users_path = Path(__file__).parent / "users/test-users.toml"
registry = TrailRegistry.from_file(Path(__file__).parent / "registry/experiments.toml")


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_start():
    username = "alex"

    with users_path.open("rb") as f:
        users = tomli.load(f)["user"]

    agent_name = users[username]["default_agent"]
    agent = await get_agent(
        agent_name,
        registry,
    )

    user_model = await User.objects.acreate(
        auth_user=await AuthUser.objects.acreate_user(
            username=username,
        ),
        default_agent_id=agent.id,
    )

    user = await get_user(user_model.auth_user.username)
    agent_session = await start_session(user)

    result = await run_from_session(agent_session, "say 'aaa'")

    assert result.output == "aaa"

    agent_session = await resume_session(user, agent_session.session.uuid)

    result = await run_from_session(agent_session, "say it again")
    assert "aaa" in str(result.output)
