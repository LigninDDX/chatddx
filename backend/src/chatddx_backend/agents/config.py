from collections.abc import Callable
from typing import Any
from typing import Callable as CallableType

from asgiref.sync import sync_to_async

from chatddx_backend.agents.schema import AgentSpec
from chatddx_backend.agents.state import agent_spec_from_data

Config = dict[str, Any]
LazyConfig = CallableType[[], Config]


def spec_from_config_sync(config: Config | LazyConfig) -> AgentSpec:
    match config:
        case dict():
            data = config
        case Callable():
            data = config()

    return agent_spec_from_data(data)


async def spec_from_config_async(config: Config | LazyConfig) -> AgentSpec:
    if isinstance(config, Callable):
        data = await resolve_config_async(config)
    else:
        data = config

    return agent_spec_from_data(data)


async def resolve_config_async(
    config: LazyConfig,
) -> Config:
    data = await sync_to_async(config, thread_sensitive=True)()
    return data
