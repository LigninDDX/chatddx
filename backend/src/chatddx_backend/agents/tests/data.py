# src/chatddx_backend/agents/tests/data.py
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli
from pydantic import BaseModel, ConfigDict

from chatddx_backend.agents.models import (
    Agent,
    Config,
    Connection,
    Message,
    Schema,
    Session,
    Tool,
)

current_dir = Path(__file__).parent


@dataclass
class LLModel:
    GEMMA3_4B = "gemma3:4b"
    GEMMA3_12B = "gemma3:12b"
    LLAMA31_8B = "llama3.1:8b"
    MEDLLAMA2_7B = "medllama2:7b"
    MISTRAL_7B = "mistral:7b"
    QWEN3_8B = "Qwen/Qwen3-8B-AWQ"  # only one actively used on vLLM, the rest are ollama string and ollama has been shut down
    QWEN3_14B = "qwen3:14b-q4_K_M"
    DEEPSEEK_8B = "deepseek-r1:8b-llama-distill-q8_0"
    DEEPSEEK_14B = "deepseek-r1:14b-qwen-distill-q4_K_M"


class TestDataSet(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    connections: dict[str, Connection]
    configs: dict[str, Config]
    schemas: dict[str, Schema]
    agents: dict[str, Agent]
    sessions: dict[str, Session]
    prompts: dict[str, str]
    tools: dict[str, Tool]


def update_set_a():
    # this was a quick fix to allow fast iterations of type_check.json while toying with the live django model
    # a cleared the migration and only use test databases atm, but but it's probably nice to have an
    # actual update_set_a at some point
    with open(current_dir / "type_check.json") as f:
        Schema.objects.filter(name="type_check").update(
            definition=json.load(f),
        )


def config_deterministic():
    return Config.objects.create(
        name="deterministic",
        temperature=1,
        top_p=1,
        seed=0,
    )


def config_no_thinking():
    return Config.objects.create(
        name="no_thinking",
        seed=0,
        provider_params={
            "extra_body": {
                "chat_template_kwargs": {
                    "enable_thinking": False,
                },
            }
        },
    )


def schema_bool():
    return Schema.objects.create(
        name="bool",
        definition={"type": "bool"},
    )


def schema_from_json(name):
    with open(current_dir / f"{name}.json") as f:
        definition = json.load(f)

    return Schema.objects.create(
        name=name,
        definition=definition,
    )


def tool_from_function(name):
    return Tool.objects.create(
        name=name,
        type=Tool.ToolType.FUNCTION,
    )


def agent_tool_coerced(name, connection, config, schema):
    return Agent.objects.create(
        name=name,
        connection=connection,
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.TOOL,
        config=config,
        schema=schema,
    )


def agent_prompt_coerced(name, connection, config, schema):
    return Agent.objects.create(
        name=name,
        connection=connection,
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.PROMPTED,
        config=config,
        schema=schema,
    )


def agent_natively_coerced(name, connection, config, schema):
    return Agent.objects.create(
        name=name,
        connection=connection,
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.NATIVE,
        config=config,
        schema=schema,
    )


def create_set_a():

    data = TestDataSet(
        connections={},
        configs={},
        schemas={},
        agents={},
        sessions={},
        prompts={},
        tools={},
    )

    data.agents["test_free_text_no_thinking"] = Agent.objects.create(
        name="test_free_text_no_thinking",
        connection=data.connections["qwen3_8b"],
        config=data.configs["no_thinking"],
    )

    data.agents["test_tools"] = Agent.objects.create(
        name="test_tools",
        connection=data.connections["qwen3_8b"],
        use_tools=True,
        config=data.configs["no_thinking"],
        instructions=(
            "You're a dice game, you should roll the die and see if the number "
            "you get back matches the user's guess. If so, tell them they're a winner. "
            "use the get_player_name tool to address the user"
        ),
    )
    data.agents["test_tools"].tools.set(
        [
            data.tools["dice"],
            data.tools["get_player_name"],
        ]
    )

    data.agents["test_tools"] = Agent.objects.prefetch_related(
        "tools",
        "connection",
        "config",
    ).get(pk=data.agents["test_tools"].pk)

    data.agents["test_tools_prime"] = Agent.objects.create(
        name="test_tools_prime",
        connection=data.connections["qwen3_8b"],
        use_tools=True,
        config=data.configs["no_thinking"],
        instructions=("use the is_prime tool to determine if user's number is a prime"),
        schema=data.schemas["bool"],
    )
    data.agents["test_tools_prime"].tools.set(
        [
            data.tools["is_prime"],
        ]
    )

    data.agents["test_tools_prime"] = Agent.objects.prefetch_related(
        "tools",
        "connection",
        "config",
        "schema",
    ).get(pk=data.agents["test_tools_prime"].pk)

    data.agents["ddx_management"] = Agent.objects.create(
        name="ddx_management",
        connection=data.connections["qwen3_8b"],
        schema=data.schemas["ddx_management"],
    )

    data.sessions["empty"] = Session.objects.create(
        description="Empty session",
    )

    message_1 = {
        "parts": [
            {
                "content": "tell me a joke",
                "timestamp": "2026-03-11T10:45:17.837860Z",
                "part_kind": "user-prompt",
            }
        ],
        "timestamp": "2026-03-11T10:45:17.838019Z",
        "instructions": None,
        "kind": "request",
        "run_id": "2d4baba8-29cd-449c-8b63-fd7df12c4910",
        "metadata": None,
    }

    message_2 = {
        "parts": [
            {
                "content": "Sure! Here's a joke for you:\n\nWhy don't skeletons fight each other?  \nBecause they don\u2019t have the *guts*! \U0001f604\n\nLet me know if you want another one!",
                "id": None,
                "provider_name": None,
                "provider_details": None,
                "part_kind": "text",
            }
        ],
        "usage": {
            "input_tokens": 16,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
            "output_tokens": 42,
            "input_audio_tokens": 0,
            "cache_audio_read_tokens": 0,
            "output_audio_tokens": 0,
            "details": {},
        },
        "model_name": "Qwen/Qwen3-8B-AWQ",
        "timestamp": "2026-03-11T10:46:35.272652Z",
        "kind": "response",
        "provider_name": "openai",
        "provider_url": "http://pelle.km:12009/v1/",
        "provider_details": {
            "finish_reason": "stop",
            "timestamp": "2026-03-11T09:55:59Z",
        },
        "provider_response_id": "chatcmpl-acdadc0038524c91",
        "finish_reason": "stop",
        "run_id": "2d4baba8-29cd-449c-8b63-fd7df12c4910",
        "metadata": None,
    }

    data.sessions["with_messages"].messages.add(
        Message.objects.create(
            role=Message.Role.USER,
            run_id=message_1["run_id"],
            payload=message_1,
            timestamp=message_1["timestamp"],
            session=data.sessions["empty"],
        ),
        Message.objects.create(
            role=Message.Role.ASSISTANT,
            run_id=message_2["run_id"],
            payload=message_2,
            timestamp=message_2["timestamp"],
            session=data.sessions["empty"],
        ),
    )
    data.prompts["case_a"] = (
        "A previously healthy 60-year-old man comes to his physician because of progressively worsening shortness of breath for the past 2 months. He does not experience shortness of breath at rest. He also occasionally has a dry cough. He has not had fever, chills, or night sweats. He has smoked a pack of cigarettes daily for the past 40 years. He drinks a beer daily and occasionally more on weekends. He does not use illicit drugs. He is 183 cm (6 ft 0 in) tall and weighs 66 kg (145 lbs); BMI is 19.7 kg/m2. His temperature is 37 °C (98.6 °F), pulse is 94/min, respirations are 21/min, and blood pressure is 136/88 mm Hg. Lung auscultation reveals a prolonged expiratory phase and end-expiratory wheezing. Spirometry shows an FEV1:FVC ratio of 62%, an FEV1 of 60% of predicted, and a total lung capacity of 125% of predicted. The diffusion capacity of the lung (DLCO) is decreased."
    )

    return data
