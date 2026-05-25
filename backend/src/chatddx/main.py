# src/chatddx/main.py
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import django
import typer

django.setup()
from chatddx.repo.shufflers.main import (
    dump_trail_registry,
    ensure_identity,
)

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
    _ = ensure_identity(owner)

    for bundle, branches in dump_trail_registry(registry, owner).items():
        for branch_idx, branch in branches.items():
            print(f"{branch.target.fingerprint}: {branch_idx} {bundle} {branch.name}:")
