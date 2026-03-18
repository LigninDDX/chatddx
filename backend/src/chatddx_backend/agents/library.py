from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli

from chatddx_backend.agents.models import Agent, Connection, Tool


@dataclass
class Library:
    agents: dict[str, Agent]
    pass


def get_library(path: Path):
    with path.open("rb") as f:
        return tomli.load(f)


library: dict[str, Any] = get_library(Path("library.toml"))


def get_connection(name: str):
    Connection.objects.create(name=name, **library["connections"][name])
    pass


def get_agent(name: str, defaults: dict[str, Any] | None = None) -> Agent:
    connection = get_connection(library["connections"][name]["connection"])
    agent = Agent.objects.create(**defaults)
    agent = Agent.objects.get(name=name)
    return agent

    if defaults is None:
        try:
            pass
        except Agent.DoesNotExist:
            pass

    c, _ = Agent.objects.update_or_create(
        name=name,
        defaults=defaults,
    )
    return c


def sync_library(filepath: str = "core_library.toml"):
    with open(filepath, "rb") as f:
        data = tomli.load(f)

    connections = {}
    for name, defaults in data.get("connections", {}).items():
        c, _ = Connection.objects.update_or_create(
            name=name,
            defaults=defaults,
        )
        connections[name] = c

    tools = {}
    for name, defaults in data.get("tools", {}).items():
        t, _ = Tool.objects.update_or_create(
            name=name,
            defaults=defaults,
        )
        tools[name] = t

    for name, conf in data.get("agents", {}).items():
        agent, _ = Agent.objects.update_or_create(
            name=name,
            defaults={
                "connection": connections[conf["connection"]],
                "use_tools": conf.get("use_tools", False),
                "instructions": conf.get("instructions", ""),
            },
        )
        if "tools" in conf:
            agent.tools.set([tools[t] for t in conf["tools"]])
