# src/chatddx/main.py
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from chatddx.django import setup  # noqa: F401 # pyright: ignore[reportUnusedImport]
from chatddx.django.repo.branches import get_branch_model
from chatddx.django.repo.models.history import IdentityModel
from chatddx.django.repo.schemas import TrailRegistry

app = typer.Typer()

init_data = typer.Typer(invoke_without_command=True)
repl = typer.Typer(invoke_without_command=True)

app.add_typer(init_data, name="init-data")
app.add_typer(repl, name="repl")


@dataclass
class Context:
    pass


@app.callback()
def main(_: typer.Context):
    pass


@init_data.callback()
def init_data_(
    _ctx: typer.Context,
    owner: Annotated[
        str,
        typer.Option(
            help="invoice id",
        ),
    ],
    registry: Annotated[
        Path,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            exists=True,
            help="location of invoice registry",
        ),
    ],
):
    trail_registry = TrailRegistry.from_file(registry)
    owner_instance, _created = IdentityModel.objects.get_or_create(name=owner)

    for kind, registry_dict in trail_registry:
        for name, schema in registry_dict.items():
            branch_model = asyncio.run(
                get_branch_model(name, owner_instance.pk, schema)
            )
            print(
                f"{kind} {name} {branch_model.pk} ({branch_model.target.fingerprint})"
            )
