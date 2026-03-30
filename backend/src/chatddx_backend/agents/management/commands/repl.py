# src/chatddx_backend/agents/management/commands/repl.py
import asyncio
from pathlib import Path
from typing import Annotated, Any

import typer
from django_typer.management import Typer
from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from pydantic_ai import (
    ModelMessage,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from rich.console import Console

from chatddx_backend.agents.main import get_agent
from chatddx_backend.agents.pydantic_ai.runners import (
    stream_from_session,
)
from chatddx_backend.agents.schemas import AgentSpec, SessionSpec, TrailRegistry
from chatddx_backend.agents.session import (
    get_identity,
    refresh_messages,
    resume_session,
    start_session,
)
from chatddx_backend.agents.trail.cache import trail_cache

app: Typer[Any, Any] = Typer()
console = Console()

registry = TrailRegistry.from_file(
    Path(__file__).parent.parent.parent / "data/registry.toml"
)


@app.command()
def main(
    owner_name: str = typer.Argument("name"),
    session_uuid: Annotated[str | None, typer.Option("--session")] = None,
    agent_name: Annotated[str | None, typer.Option("--agent")] = None,
):
    """
    Start a repl with an agent
    """

    owner = asyncio.run(get_identity(owner_name))
    agent = asyncio.run(get_agent(agent_name, registry)) if agent_name else None

    if session_uuid:
        session = asyncio.run(resume_session(owner, session_uuid))
        if not agent:
            agent = session.default_agent
    else:
        assert agent
        session = asyncio.run(start_session(owner, agent))

    run_repl(session, agent)


def run_repl(session: SessionSpec, agent: AgentSpec):
    print(f"session id: {session.uuid}")
    print(f"agent: {agent.name}")

    for message in session.messages:
        msg_agent = asyncio.run(trail_cache.get_instance(AgentSpec, message.agent_id))
        print_message(message.payload, msg_agent)

    async def consume_and_print(user_prompt: str):
        console.print(agent.name, style="#FFFFFF")

        stream_gen = stream_from_session(
            session,
            user_prompt,
            agent_spec=agent,
        )

        thunk = False
        content = ""
        async for chunk, _ in stream_gen:
            for part in chunk.parts:
                match part:
                    case ThinkingPart(value):
                        if not thunk:
                            print("Thinking:", value)
                            thunk = True
                    case TextPart(value):
                        delta = value[len(content) :]
                        content = value
                        console.print(delta, end="", style="#886622")
                    case _:
                        raise ValueError(f"No handler for {type(part)}")
        print()

    while True:
        prompt_ = prompt(
            "> ",
            history=FileHistory("history.txt"),
            auto_suggest=AutoSuggestFromHistory(),
        )
        asyncio.run(consume_and_print(prompt_))
        asyncio.run(refresh_messages(session))


def print_message(message: ModelMessage, agent: AgentSpec, skip_text: bool = False):
    content: list[tuple[str, str]] = []
    assert message.timestamp

    if not skip_text:
        content.extend(
            [
                (agent.name, "#FFFFFF"),
                (f"======{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}======", ""),
            ]
        )

    kind = message.kind
    for part in message.parts:
        match kind, part:
            case "response", ThinkingPart():
                content.append((part.content, "#226688"))
            case "response", TextPart():
                if not skip_text:
                    content.append((part.content, "#886622"))
            case "request", UserPromptPart():
                content.append((str(part.content), "#882266"))
            case "response", ToolCallPart():
                content.append((str(part), "#662288"))
            case "request", ToolReturnPart():
                content.append((str(part), "#662288"))
            case _:
                raise ValueError(f"unhandled kind-part tuple ({kind}, {type(part)})")

    for s, c in content:
        console.print(s, style=c)
