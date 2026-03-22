from typing import Any

import pytest

from chatddx_backend.agents.library import (
    LibraryParser,  # Assuming this is where it lives
)
from chatddx_backend.agents.schema import (
    AgentIn,
    ConnectionIn,
    OutputTypeIn,
    SamplingParamsIn,
    ToolGroupIn,
    ToolIn,
)


@pytest.fixture
def mock_library():
    """Provides a realistic mock of the nested library dictionary."""
    return {
        "connection": {
            "test_openai": {
                "provider": "openai",
                "model": "gpt-4-turbo",
                "endpoint": "https://api.openai.com/v1",
            }
        },
        "tool": {
            "search_tool": {
                "description": "Searches the web",
                "type": "function",
                "parameters": {"type": "object"},  # Minimal valid JSON schema
            }
        },
        "tool_group": {
            "web_group": {
                "instructions": "Use the search tool for recent events.",
                "tools": ["search_tool"],  # List of string references
            }
        },
        "sampling_params": {"creative": {"temperature": 0.9, "top_p": 1.0}},
        "output_type": {
            "json_output": {
                "definition": {"type": "object"}  # Minimal valid JSON schema
            }
        },
        "agent": {
            "complex_agent": {
                "instructions": "You are an advanced assistant.",
                "use_tools": True,
                "validation_strategy": "strict",
                "coercion_strategy": "retry",
                # These reference strings in the library
                "connection": "test_openai",
                "tool_group": "web_group",
                "sampling_params": "creative",
                "output_type": "json_output",
            },
            "minimal_agent": {
                "instructions": "You are a simple chatbot.",
                "use_tools": False,
                "validation_strategy": "none",
                "coercion_strategy": "none",
                # Connection, tool_group, etc., are explicitly missing
            },
        },
    }


def test_parser_extracts_simple_schema(mock_library: dict[str, Any]):
    """Ensures base schemas without nesting are parsed correctly."""
    parser = LibraryParser(library=mock_library)
    conn = parser.get_instance(ConnectionIn, "test_openai")

    assert isinstance(conn, ConnectionIn)
    assert conn.name == "test_openai"
    assert conn.provider == "openai"
    assert conn.model == "gpt-4-turbo"


def test_parser_extracts_nested_list_of_schemas(mock_library: dict[str, Any]):
    """Ensures `list[ToolIn]` correctly maps a list of strings to a list of instances."""
    parser = LibraryParser(library=mock_library)
    tool_group = parser.get_instance(ToolGroupIn, "web_group")

    assert isinstance(tool_group, ToolGroupIn)
    assert tool_group.name == "web_group"
    assert len(tool_group.tools) == 1

    # Check the nested tool
    tool = tool_group.tools[0]
    assert isinstance(tool, ToolIn)
    assert tool.name == "search_tool"
    assert tool.type == "function"


def test_parser_extracts_fully_nested_agent(mock_library: dict[str, Any]):
    """Ensures the recursive parsing works for the entire tree."""
    parser = LibraryParser(library=mock_library)
    agent = parser.get_instance(AgentIn, "complex_agent")

    assert isinstance(agent, AgentIn)
    assert agent.name == "complex_agent"
