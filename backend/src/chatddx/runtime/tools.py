from pydantic_ai import RunContext

from chatddx.runtime.context import AgentContext


def sentinel_string(_: RunContext[AgentContext]) -> str:
    """This is tool returns a string that is hard to know in advance"""
    return "asdf"


def sentinel_op(_: RunContext[AgentContext], v1: int, v2: int) -> float:
    """This tool takes two arguments and performs an operation on them"""
    return v1 % v2


def user_details(_: RunContext[AgentContext]) -> str:
    """Run this function to get user's name"""
    return "pelle"


def is_prime(_: RunContext[AgentContext], x: int) -> bool:
    """Takes an integer x and returns True if it's a prime and False otherwise"""
    return x == 15
