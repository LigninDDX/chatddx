import asyncio
from pathlib import Path
from typing import Any

from django_typer.management import Typer

from chatddx_backend.agents.models.agent import AgentModel
from chatddx_backend.agents.schemas import AgentSchema, TrailRegistry
from chatddx_backend.agents.trail import model_from_schema

app: Typer[Any, Any] = Typer()


@app.command()
def main(path: Path):
    """
    Copy a registry to database
    """
    registry = TrailRegistry.from_file(path)

    for agent in registry.agent:
        agent_schema = registry.get(AgentSchema, agent)
        agent_model = asyncio.run(model_from_schema(AgentModel, agent_schema))
        print(f"Immutable record upsert: {agent_model.pk} ({agent_model.fingerprint})")

        mutable_agent_model = asyncio.run(
            model_from_schema(AgentModel, agent_schema, mutable=True)
        )
        print(f"Mutable record upsert: {mutable_agent_model.pk}")
