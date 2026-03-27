import json
from pathlib import Path

import pytest

from chatddx_backend.agents.main import agent_spec
from chatddx_backend.agents.pydantic_ai.runners import run_async
from chatddx_backend.agents.schemas import TrailRegistry
from chatddx_backend.agents.utils import Dispatcher

registry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/ddx-management.toml"
)
dispatcher = Dispatcher()


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_ddx_management():
    data_path = Path(__file__).parent / "cases/case_a.txt"
    expects_path = Path(__file__).parent / "expects/case_a.json"

    with data_path.open("r") as f:
        case_a = f.read()

    with expects_path.open("r") as f:
        data = json.load(f)

    spec = await agent_spec("ddx-management", registry)
    result = await run_async(spec, case_a, dispatcher)

    print(json.dumps(result.output, indent=2))
    assert result.output == data
