from decimal import Decimal
from pathlib import Path

import pytest

from chatddx_backend.agents.registry import ParseError
from chatddx_backend.agents.schemas import AgentSchema, ConnectionSchema, TrailRegistry

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-registry.toml"
)


def test_properties():
    agent_1 = registry.get(AgentSchema, "agent-1")
    assert agent_1.name == "agent-1"
    assert agent_1.tool_group
    assert agent_1.tool_group.name == "tool_group-1"
    assert agent_1.tool_group.tools[0].name == "tool-1"


def test_some_properties():
    some_connection = registry.get(ConnectionSchema, "some-connection")
    assert some_connection.name == "some-connection"


def test_extended_registries():
    agent_1 = registry.get(AgentSchema, "tools-prime")
    assert agent_1.name == "tools-prime"
    assert agent_1.tool_group.name == "default"


def test_merged_properties():
    agent_2 = registry.get(AgentSchema, "agent-2")
    assert agent_2.name == "agent-2"
    assert agent_2.sampling_params
    assert agent_2.sampling_params.name == "sampling_params-1|sampling_params-2"
    assert agent_2.sampling_params.temperature == Decimal("0.7")
    assert agent_2.sampling_params.max_tokens == 150
    assert agent_2.sampling_params.seed == 0
    assert agent_2.sampling_params.stop_sequences == ["\\n\\n", "END"]


def test_extended_records():
    agent_3 = registry.get(AgentSchema, "agent-3")
    assert agent_3.name == "agent-3|agent-1|agent-2"
    assert agent_3.instructions == "hello 3"
    assert agent_3.sampling_params
    assert agent_3.sampling_params.name == "sampling_params-1"
    assert agent_3.tool_group
    assert agent_3.tool_group.name == "tool_group-1"
    assert agent_3.tool_group.tools[0].name == "tool-1"


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

    infrec_1 = infrec_registry.get(AgentSchema, "agent-1")
    assert infrec_1.name == "agent-1|agent-2"
    assert infrec_1.instructions == "agent 1"
