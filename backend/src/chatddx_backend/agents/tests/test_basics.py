from pathlib import Path

import pytest

from chatddx_backend.agents.main import agent_spec
from chatddx_backend.agents.pydantic_ai.runners import run_from_spec
from chatddx_backend.agents.schemas import TrailRegistry
from chatddx_backend.agents.utils import Dispatcher

registry = TrailRegistry.from_file(Path(__file__).parent / "registry/experiments.toml")
dispatcher = Dispatcher()


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_tool_coerced():
    spec = await agent_spec("tool-coerced", registry)

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_from_spec(spec, prompt)

    assert result.output == {
        "bool": True,
        "integer": 123,
        "list": [
            "string",
            "string",
        ],
    }


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_prompt_coerced():
    spec = await agent_spec("prompt-coerced", registry)

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_from_spec(spec, prompt)

    assert result.output == {
        "__error__": "'string' is not of type 'integer'",
        "bool": 1,
        "integer": "string",
        "list": [
            "boolean",
        ],
    }


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_native_coerced():
    spec = await agent_spec("native-coerced", registry)

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_from_spec(spec, prompt)

    assert isinstance(result.output, dict)

    assert result.output == {
        "bool": True,
        "integer": 42,
        "list": [
            "string1",
            "string2",
        ],
    }


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_no_thinking():
    spec = await agent_spec("no-thinking", registry)

    prompt = "this message is a result of automated testing, respond with '123abc'."

    result = await run_from_spec(spec, prompt)

    assert result.response.thinking is None
    assert result.output == "123abc"


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_thinking():
    spec = await agent_spec("thinking", registry)

    prompt = "this message is a result of automated testing, respond with '123abc'."

    result = await run_from_spec(spec, prompt)

    assert result.response.thinking
    assert isinstance(result.output, str)
    assert result.output == "\n\n123abc"
