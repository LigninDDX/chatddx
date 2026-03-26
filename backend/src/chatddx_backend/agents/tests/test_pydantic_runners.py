import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import ModelMessagesTypeAdapter

from chatddx_backend.agents.pydantic_ai.runners import run_async, run_sync
from chatddx_backend.agents.registry import load_registry
from chatddx_backend.agents.runtime import agent_spec

registry: dict[str, Any] = load_registry(
    Path(__file__).parent / "registry" / "experiments.toml"
)


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_ddx_management():
    data_path = Path(__file__).parent / "cases/case_a.txt"
    with open(data_path, "r") as f:
        case_a = f.read()

    spec = await agent_spec("ddx-management", registry)
    result = await run_async(spec, case_a)

    assert result.output == ""


@pytest.mark.asyncio
async def test_structure_tool(self):
    a = self.data.agents["test_structure_tool"]
    assert str(a) == "test_structure_tool"

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_async(a, prompt)

    assert isinstance(result.output, dict)

    assert result.output == {
        "bool": True,
        "integer": 42,
        "list": [
            "violate",
            "the",
            "dictated",
            "response",
            "type",
            "number",
            "->",
            "string",
            "and",
            "boolean",
            "->",
            "number",
        ],
    }


@pytest.mark.asyncio
async def test_structure_prompted(self):
    a = self.data.agents["test_structure_prompted"]
    assert str(a) == "test_structure_prompted"

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_async(a, prompt)

    assert isinstance(result.output, dict)

    assert result.output == {
        "__error__": "'456' is not of type 'integer'",
        "bool": 1,
        "integer": "456",
        "list": [
            "apple",
            "banana",
        ],
    }


@pytest.mark.asyncio
async def test_structure_native(self):
    a = self.data.agents["test_structure_native"]
    assert str(a) == "test_structure_native"

    prompt = "violate the dictated response type number -> string and boolean -> number"

    result = await run_async(a, prompt)

    assert isinstance(result.output, dict)

    assert result.output == {
        "bool": True,
        "integer": 42,
        "list": ["a", "b", "c"],
    }


@pytest.mark.asyncio
async def test_no_structure(self):
    a = self.data.agents["test_free_text_no_thinking"]
    assert str(a) == "test_free_text_no_thinking"

    prompt = "this message is a result of automated testing, respond with '123abc'."

    result = await run_async(a, prompt)

    assert isinstance(result.output, str)

    assert result.response.thinking is None
    assert result.output.strip() == "123abc"


@pytest.mark.asyncio
async def test_tools(self):
    a = self.data.agents["test_tools"]
    assert str(a) == "test_tools"
    prompt = "My guess is four"
    result = await run_async(a, prompt)
    assert result.response.thinking is None
    assert isinstance(result.output, str)
    assert "pelle" in result.output.lower()
    assert "5.5" in result.output


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


def test_message_spec(self):
    a = self.data.agents["test_structure_native"]
    assert str(a) == "test_structure_native"
    assert a.connection is not None

    prompt = ""

    result = run_sync(a, prompt)

    assert result.output == {
        "bool": True,
        "integer": 42,
        "list": ["item1", "item2", "item3"],
    }

    messages = json.loads(result.new_messages_json())

    req_msg, res_msg = messages

    assert type(messages) == list

    assert list(req_msg.keys()) == [
        "parts",
        "timestamp",
        "instructions",
        "kind",
        "run_id",
        "metadata",
    ]
    assert list(res_msg.keys()) == [
        "parts",
        "usage",
        "model_name",
        "timestamp",
        "kind",
        "provider_name",
        "provider_url",
        "provider_details",
        "provider_response_id",
        "finish_reason",
        "run_id",
        "metadata",
    ]

    assert req_msg["kind"] == "request"
    assert res_msg["kind"] == "response"

    # e.g. 6d29a548-7ae2-4ed1-bfd6-bda4300939fa
    assert res_msg["run_id"] == req_msg["run_id"]

    (req_part,) = req_msg["parts"]
    (res_part,) = res_msg["parts"]

    assert list(req_part.keys()) == [
        "content",
        "timestamp",
        "part_kind",
    ]

    assert list(res_part.keys()) == [
        "content",
        "id",
        "provider_name",
        "provider_details",
        "part_kind",
    ]

    assert req_part["part_kind"] == "user-prompt"
    assert res_part["part_kind"] == "text"

    assert req_part["content"] == prompt
    assert json.loads(res_part["content"]) == result.output

    assert req_msg["metadata"] == None
    assert res_msg["metadata"] == None

    # ModelResponse only
    assert res_part["id"] == None
    assert res_part["provider_name"] == None
    assert res_part["provider_details"] == None
    assert res_msg["provider_name"] == "openai"
    assert res_msg["provider_url"] == a.connection.endpoint
    assert res_msg["model_name"] == a.connection.model
    assert res_msg["finish_reason"] == "stop"

    res_usage = res_msg["usage"]
    assert list(res_usage.keys()) == [
        "input_tokens",
        "cache_write_tokens",
        "cache_read_tokens",
        "output_tokens",
        "input_audio_tokens",
        "cache_audio_read_tokens",
        "output_audio_tokens",
        "details",
    ]

    assert res_usage["input_tokens"] == 8
    assert res_usage["output_tokens"] == 37
    assert res_usage["cache_read_tokens"] == 0
    assert res_usage["cache_write_tokens"] == 0
    assert res_usage["details"] == {}

    res_provider = res_msg["provider_details"]
    assert list(res_provider.keys()) == [
        "finish_reason",
        "timestamp",
    ]

    assert res_provider["finish_reason"] == "stop"

    # Timestamps
    # e.g. 2026-02-27T19:59:09.600729Z
    req_msg_t = datetime.fromisoformat(req_msg["timestamp"])
    res_msg_t = datetime.fromisoformat(res_msg["timestamp"])
    assert req_msg_t < res_msg_t

    req_part_t = datetime.fromisoformat(req_part["timestamp"])
    assert req_part_t < req_msg_t

    res_provider_t = datetime.fromisoformat(res_provider["timestamp"])
    assert res_provider_t < res_msg_t
