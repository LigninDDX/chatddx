import asyncio
from pathlib import Path
from typing import Any

from django.contrib.auth.models import User as AuthUser
from django_typer.management import Typer

from chatddx_backend.agents.models import Agent, User
from chatddx_backend.agents.schemas import AgentSchema, TrailRegistry
from chatddx_backend.agents.trail import model_from_schema

app: Typer[Any, Any] = Typer()

registry = TrailRegistry.from_file(
    Path(__file__).parent.parent.parent / "tests/registry/experiments.toml"
)


@app.command()
def main(name: str, default_agent: str):
    """
    Init agent user
    """
    auth_user = AuthUser.objects.get(username=name)
    agent_schema = registry.get(AgentSchema, default_agent)
    agent_model = asyncio.run(model_from_schema(Agent, agent_schema))
    user, _ = User.objects.update_or_create(
        auth_user=auth_user,
        defaults={
            "default_agent": agent_model,
        },
    )
    print(f"Init user {user.auth_user.username} with agent {agent_model.name}")
