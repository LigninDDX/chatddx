from pydantic_ai import RunContext

from chatddx_backend.agents.pydantic_ai.context import AgentContext


def dice(ctx: RunContext[AgentContext]) -> int:
    """This dice is broken and only returns 3"""
    return 3


def user_details(ctx: RunContext[AgentContext]) -> str:
    """Run this function to get user's name"""
    return "pelle"


def is_prime(ctx: RunContext[AgentContext], x: int) -> bool:
    """Takes an integer x and returns True if it's a prime and False otherwise"""
    return x == 15
