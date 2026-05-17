# src/chatddx/backend/repo/test/test_llm_basics.py
from pathlib import Path

import pytest
import pytest_asyncio

from chatddx.django.repo.main import get_agent
from chatddx.django.repo.models import IdentityModel
from chatddx.django.repo.models.history import AgentBranchModel
from chatddx.django.repo.pydantic_ai.runners import run_from_session, run_from_spec
from chatddx.django.repo.schemas import TrailRegistry
from chatddx.django.repo.session import get_identity, resume_session, start_session
from chatddx.django.repo.utils import Dispatcher

registry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-llm-basics.toml"
)
dispatcher = Dispatcher()


@pytest_asyncio.fixture
async def owner():
    owner, created = await IdentityModel.objects.aget_or_create(name="alex")
    return owner


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_tool_coerced():
    spec = await get_agent("tool-coerced", registry)

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
    spec = await get_agent("prompt-coerced", registry)

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
    spec = await get_agent("native-coerced", registry)

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
    spec = await get_agent("no-thinking", registry)

    prompt = "this message is a result of automated testing, respond with '123abc'."

    result = await run_from_spec(spec, prompt)

    assert result.response.thinking is None
    assert result.output == "123abc"


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_thinking():
    spec = await get_agent("thinking", registry)

    prompt = "this message is a result of automated testing, respond with '123abc'."

    result = await run_from_spec(spec, prompt)

    assert result.response.thinking
    assert isinstance(result.output, str)
    assert result.output == "\n\n123abc"


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_tool_call():
    spec = await get_agent("tools-sentinel", registry)

    prompt = "1) run 'sentinel_string' and tell me the result"
    prompt += "2) run 'sentinel_op' with 12 and 8 and tell me the result"

    result = await run_from_spec(spec, prompt)

    assert "asdf" in str(result.output)
    assert "4" in str(result.output)


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_session(owner):
    agent = await get_agent("no-thinking", registry)

    agent_branch = await AgentBranchModel.objects.acreate(
        name="no-thinking",
        owner_id=owner.id,
        target_id=agent.id,
    )
    session = await start_session(owner.id, agent_branch.id)

    result = await run_from_session(session, "say 'aaa'")

    assert result.output == "aaa"

    agent_session = await resume_session(owner.id, session.uuid)

    result = await run_from_session(agent_session, "say it again")
    assert "aaa" in str(result.output)
