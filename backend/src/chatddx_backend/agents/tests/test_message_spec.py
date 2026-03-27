import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic_ai import AgentRunResult

from chatddx_backend.agents.main import agent_spec
from chatddx_backend.agents.pydantic_ai.runners import run_async
from chatddx_backend.agents.schemas import TrailRegistry
from chatddx_backend.agents.utils import Dispatcher

registry = TrailRegistry.from_file(Path(__file__).parent / "registry/experiments.toml")
dispatcher = Dispatcher()


def hello(r: AgentRunResult):
    print(r)
    raise


dispatcher.subscribe(hello)


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_message_spec():
    spec = await agent_spec("no-thinking", registry)
    assert spec.connection

    prompt = "hello"
    result = await run_async(spec, prompt, dispatcher)

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
    assert res_part["content"] == result.output

    assert req_msg["metadata"] == None
    assert res_msg["metadata"] == None

    # ModelResponse only
    assert res_part["id"] == None
    assert res_part["provider_name"] == None
    assert res_part["provider_details"] == None
    assert res_msg["provider_name"] == "openai"
    assert res_msg["provider_url"] == spec.connection.endpoint
    assert res_msg["model_name"] == spec.connection.model
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

    assert res_usage["input_tokens"] == 13
    assert res_usage["output_tokens"] == 12
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
