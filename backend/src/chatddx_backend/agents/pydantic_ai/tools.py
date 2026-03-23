from pydantic_ai import RunContext

from chatddx_backend.agents.pydantic_ai.context import AgentContext


def dice(ctx: RunContext[AgentContext]) -> str:
    return "5.5"


def get_player_name(ctx: RunContext[AgentContext]) -> str:
    """Fetches the current user's name from the active session."""
    return "pelle"


def is_prime(ctx: RunContext[AgentContext], x: int) -> bool:
    """Takes an integer x and returns True if it's a prime and False otherwise"""
    return x == 15
