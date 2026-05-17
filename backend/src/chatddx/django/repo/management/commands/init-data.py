# src/chatddx/django/repo/management/commands/init-data.py
import asyncio
from pathlib import Path
from typing import Any

from django_typer.management import Typer
from repo.models import IdentityModel

from chatddx.django.repo.branches import get_branch_model
from chatddx.django.repo.schemas import TrailRegistry

app: Typer[Any, Any] = Typer()


@app.command()
def main(path: Path, owner_name: str):
    """
    Copy a registry to database
    """
    registry = TrailRegistry.from_file(path)
    owner, created = IdentityModel.objects.get_or_create(name=owner_name)
    for kind, registry_dict in registry:
        for agent_name, agent_schema in registry_dict.items():
            branch_model = asyncio.run(
                get_branch_model(agent_name, owner.pk, agent_schema)
            )
            print(
                f"{kind} {agent_name} {branch_model.pk} ({branch_model.target.fingerprint})"
            )
