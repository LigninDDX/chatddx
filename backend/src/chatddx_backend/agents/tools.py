from pydantic_ai import RunContext

from chatddx_backend.agents.types import AgentDeps


def dice(ctx: RunContext[AgentDeps]) -> str:
    return "5.5"


def get_player_name(ctx: RunContext[AgentDeps]) -> str:
    """Fetches the current user's name from the active session."""
    return "pelle"


def is_prime(ctx: RunContext[AgentDeps], x: int) -> bool:
    """Takes an integer x and returns True if it's a prime and False otherwise"""
    return x == 15
