# src/chatddx/main.py
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import django
import typer

django.setup()

from chatddx.core.models import IdentityModel
from chatddx.registry.schemas import TrailRegistry
from chatddx.repo.loaders.branches import branch_from_trail

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
            branch_model = branch_from_trail(kind, name, owner_instance.name, schema)
            branch_model.save()
            print(
                f"{kind} {name} {branch_model.pk} ({branch_model.target.fingerprint})"
            )
