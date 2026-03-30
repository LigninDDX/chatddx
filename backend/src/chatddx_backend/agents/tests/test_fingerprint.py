from pathlib import Path

from chatddx_backend.agents.schemas import AgentSchema, TrailRegistry

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-registry.toml"
)


def test_properties():
    agent_1 = registry.get(AgentSchema, "agent-1")
    assert agent_1.name == "agent-1"
    assert agent_1.tool_group
    assert agent_1.tool_group.name == "tool_group-1"
    assert agent_1.tool_group.tools[0].name == "tool-1"

    fingerprint = agent_1.fingerprint

    agent_1_ = registry.get(AgentSchema, "agent-1")
    assert agent_1_.fingerprint == fingerprint

    agent_1_.instructions += "a"
    assert agent_1_.fingerprint != fingerprint
