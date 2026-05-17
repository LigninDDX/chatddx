# src/chatddx/backend/repo/test/test_message_spec.py
from decimal import Decimal
from pathlib import Path

import pytest

from chatddx.django.repo.models import ToolChoices
from chatddx.django.repo.registry import ParseError
from chatddx.django.repo.schemas import AgentSchema, ConnectionSchema, TrailRegistry

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-registry.toml"
)


def test_loader():
    pass


def test_properties():
    agent_1 = registry.get_by_type(AgentSchema, "agent-1")
    assert agent_1.instructions == "hello 1"
    assert agent_1.tool_group
    assert agent_1.tool_group.instructions == "use these tools"
    assert agent_1.tool_group.tools[0].type == ToolChoices.FUNCTION


def test_some_properties():
    some_connection = registry.get_by_type(ConnectionSchema, "some-connection")
    assert some_connection.model == "Some/model"


def test_extended_registries():
    agent_1 = registry.get_by_type(AgentSchema, "some-agent")
    assert agent_1.instructions == "some instructions"
    assert agent_1.tool_group.instructions == "some tool group instructions"


def test_merged_properties():
    agent_2 = registry.get_by_type(AgentSchema, "agent-2")
    assert agent_2.instructions == "hello 2"
    assert agent_2.sampling_params
    assert agent_2.sampling_params.temperature == Decimal("0.7")
    assert agent_2.sampling_params.max_tokens == 150
    assert agent_2.sampling_params.seed == 0
    assert agent_2.sampling_params.stop_sequences == ["\\n\\n", "END"]


def test_extended_records():
    agent_3 = registry.get_by_type(AgentSchema, "agent-3")
    assert agent_3.instructions == "hello 3"
    assert agent_3.sampling_params
    assert agent_3.tool_group
    assert agent_3.tool_group.instructions == "use these tools"
    assert agent_3.tool_group.tools[0].type == ToolChoices.FUNCTION


def test_infrec_file():
    with pytest.raises(ParseError):
        infrec_registry: TrailRegistry = TrailRegistry.from_file(
            Path(__file__).parent / "registry/infrec-1.toml"
        )
        assert infrec_registry


def test_infrec_record():
    infrec_registry: TrailRegistry = TrailRegistry.from_file(
        Path(__file__).parent / "registry/infrec-4.toml"
    )

    infrec_1 = infrec_registry.get_by_type(AgentSchema, "agent-1")
    assert infrec_1.instructions == "agent 1"
