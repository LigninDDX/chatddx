# src/chatddx_backend/agents/management/commands/repl.py
import asyncio
from pathlib import Path
from typing import Any

from django_typer.management import Typer
from pydantic_ai import ModelMessage, TextPart, ThinkingPart, UserPromptPart
from rich.console import Console

from chatddx_backend.agents.main import get_agent
from chatddx_backend.agents.models import Session
from chatddx_backend.agents.pydantic_ai.runners import (
    stream_from_session,
)
from chatddx_backend.agents.schemas import AgentSpec, TrailRegistry
from chatddx_backend.agents.session import (
    AgentSession,
    get_user,
    refresh_messages,
    resume_session,
    start_session,
)
from chatddx_backend.agents.trail.cache import trail_cache
from chatddx_backend.agents.utils import Dispatcher

app: Typer[Any, Any] = Typer()
console = Console()

registry = TrailRegistry.from_file(
    Path(__file__).parent.parent.parent / "tests/registry/experiments.toml"
)


@app.command()
def main(
    user: str,
    session: str | None = None,
    agent: str | None = None,
):
    """
    Start a repl with an agent
    """
    user_spec = asyncio.run(get_user(user))

    if agent:
        agent_spec = asyncio.run(get_agent(agent, registry))
    else:
        agent_spec = None

    if session is not None:
        uuid = Session.objects.get(
            user_id=user_spec.id,
            uuid__startswith=session,
        ).uuid
        agent_session = asyncio.run(resume_session(user_spec, uuid, agent_spec))
    else:
        agent_session = asyncio.run(start_session(user_spec, agent_spec))

    run_repl(agent_session)


def run_repl(agent_session: AgentSession):
    print(f"In session {agent_session.session.uuid}")
    console.print(agent_session.agent.name, style="#FFFFFF")

    dispatcher = Dispatcher()

    def on_any(data: Any):
        pass

    dispatcher.subscribe(on_any)

    for message in agent_session.session.messages:
        msg_agent = trail_cache.get_instance(AgentSpec, message.agent_id)
        print_message(message.payload, msg_agent)

    async def consume_and_print(user_prompt: str):
        console.print(agent_session.agent.name, style="#FFFFFF")

        stream_gen = stream_from_session(agent_session, user_prompt, dispatcher)

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
        prompt = input("> ")
        asyncio.run(consume_and_print(prompt))
        asyncio.run(refresh_messages(agent_session))


def print_message(message: ModelMessage, agent: AgentSpec, skip_text: bool = False):
    content: list[tuple[str, str]] = []

    # Only print the header if we aren't skipping text.
    # (If we are skipping text, the REPL loop already printed the header before streaming)
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
                # Ignore the text part if it was already streamed
                if not skip_text:
                    content.append((part.content, "#886622"))
            case "request", UserPromptPart():
                content.append((str(part.content), "#882266"))
            case _:
                raise ValueError(f"unhandled kind-part tuple ({kind}, {type(part)})")

    for s, c in content:
        console.print(s, style=c)
