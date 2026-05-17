import json
from pathlib import Path

import pytest

from chatddx_backend.agents.main import get_agent
from chatddx_backend.agents.pydantic_ai.runners import run_from_spec
from chatddx_backend.agents.schemas import TrailRegistry

registry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/ddx-management.toml"
)


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_ddx_management():
    data_path = Path(__file__).parent / "cases/case_a.txt"
    expects_path = Path(__file__).parent / "expects/case_a.json"

    with data_path.open("r") as f:
        case_a = f.read()

    with expects_path.open("r") as f:
        data = json.load(f)

    spec = await get_agent("ddx-management", registry)
    result = await run_from_spec(spec, case_a)

    print(json.dumps(result.output, indent=2))
    assert result.output == data
