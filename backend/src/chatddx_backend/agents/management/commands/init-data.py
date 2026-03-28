import asyncio
from pathlib import Path
from typing import Any

from django_typer.management import Typer

from chatddx_backend.agents.models.agent import Agent
from chatddx_backend.agents.schemas import AgentSchema, TrailRegistry
from chatddx_backend.agents.trail import model_from_schema

app: Typer[Any, Any] = Typer()


@app.command()
def main(path: Path):
    """
    A basic command that uses Typer
    """
    registry = TrailRegistry.from_file(path)
    for k in registry.agent:
        agent_schema = registry.get(AgentSchema, k)
        agent_model = asyncio.run(model_from_schema(Agent, agent_schema))
        print(f"Immutable record upsert: {agent_model.pk} ({agent_model.fingerprint})")

        mutable_agent_model = asyncio.run(
            model_from_schema(Agent, agent_schema, mutable=True)
        )
        print(f"Mutable record upsert: {mutable_agent_model.pk}")
