from typing import Any

from django_typer.management import Typer

from chatddx_backend.agents.models import IdentityModel

app: Typer[Any, Any] = Typer()


@app.command()
def main(name: str):
    """
    Init identity
    """
    identity, update = IdentityModel.objects.update_or_create(
        name=name,
    )
    if update:
        print(f"Created identity '{identity.name}'")
    else:
        print(f"Updated identity '{identity.name}'")
