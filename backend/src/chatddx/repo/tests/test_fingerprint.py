# src/chatddx/backend/repo/test/test_fingerprint.py
from pathlib import Path

from chatddx.registry.schemas import TrailRegistry
from chatddx.repo.trail_schemas import AgentSchema

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "data/test-registry.toml"
)


def test_properties():
    agent_1 = registry.get_by_type(AgentSchema, "agent-1")
    assert agent_1.tool_group

    fingerprint = agent_1.fingerprint

    agent_1_ = registry.get_by_type(AgentSchema, "agent-1")
    assert agent_1_.fingerprint == fingerprint

    agent_1_.instructions += "a"
    assert agent_1_.fingerprint != fingerprint
