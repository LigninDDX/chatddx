from pathlib import Path

import pytest
from pydantic_ai import ModelMessagesTypeAdapter

from chatddx_backend.agents.main import agent_spec
from chatddx_backend.agents.pydantic_ai.runners import run_async, run_sync
from chatddx_backend.agents.schemas import TrailRegistry

registry = TrailRegistry.from_file(Path(__file__).parent / "registry/experiments.toml")


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_tool_group_dice():
    spec = await agent_spec("tools-dice", registry)
    prompt = "guess my name, roll a dice, my guess is 4"
    result = await run_async(spec, prompt)
    assert result.response.thinking is None
    assert isinstance(result.output, str)
    assert result.output.lower() == ""


@pytest.mark.asyncio
async def test_tools_with_parameters(self):
    a = self.data.agents["test_tools_prime"]
    assert str(a) == "test_tools_prime"
    prompt = "Is 15 a prime number?"
    result = await run_async(a, prompt)
    assert result.response.thinking is None
    assert result.output == True

    prompt = "Is 13 a prime number?"
    result = await run_async(a, prompt)
    assert result.output == False


def test_conversation(self):
    a = self.data.agents["test_free_text_no_thinking"]
    s = self.data.sessions["empty"]

    assert a.connection is not None

    run_id = "2d4baba8-29cd-449c-8b63-fd7df12c4910"
    messages = ModelMessagesTypeAdapter.validate_python(
        [
            m.payload
            for m in s.messages.filter(
                run_id=run_id,
            )
        ]
    )
    assert len(messages) == 2
    assert messages[0].run_id == run_id
    assert messages[1].run_id == run_id

    assert messages[0].parts[0].content == "tell me a joke"
    assert "another one" in messages[1].parts[0].content

    prompt = "explain"
    result = run_sync(a, prompt, messages)
    assert "guts!" in str(result.output)

    messages = result.new_messages()

    assert messages[0].parts[0].content == "explain"
    assert messages[1].parts[0].content == result.output
