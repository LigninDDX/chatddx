# src/chatddx/repl.py
import asyncio
from typing import Annotated, Any

import typer
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

from chatddx.history.models import SessionModel
from chatddx.history.schemas import SessionSpec
from chatddx.history.session import refresh_messages, resume_session, start_session
from chatddx.repo.base import BranchSpec
from chatddx.repo.branch_models import AgentBranchModel
from chatddx.repo.shufflers.main import ensure_identity
from chatddx.repo.trail_specs import AgentSpec
from chatddx.runtime.runners import stream_from_session

app = typer.Typer(invoke_without_command=True)
console = Console()


@app.callback()
def main(
    owner_name: Annotated[str, typer.Argument()],
    session_uuid: Annotated[str | None, typer.Option("--session")] = None,
    agent_name: Annotated[str | None, typer.Option("--agent")] = None,
):
    """
    Start a repl with an agent
    """

    owner = ensure_identity(owner_name)

    if session_uuid is None and agent_name is None:
        typer.echo("Error: You must provide either --session or --agent or both.")
        typer.secho("\nAvailable agents:", bold=True)
        for agent in AgentBranchModel.objects.filter(owner_id=owner.id):
            typer.echo(agent.name)

        typer.secho("\nAvailable sessions:", bold=True)
        for session in SessionModel.objects.filter(owner_id=owner.id):
            typer.echo(
                f"{session.uuid} {session.timestamp.strftime('%Y-%m-%d %H:%M')} {session.default_agent.name} {len(session.messages.all())}"
            )

        return

    if session_uuid:
        session = asyncio.run(resume_session(owner.id, session_uuid))
        if not agent_name:
            agent_branch = session.default_agent

    if agent_name:
        agent_branch = BranchSpec[AgentSpec].model_validate(
            AgentBranchModel.objects.filter(name=agent_name, owner_id=owner.id).latest(
                "timestamp"
            )
        )
        if not session_uuid:
            session = asyncio.run(start_session(owner.id, agent_branch.id))

    run_repl(session, agent_branch)


def run_repl(session: SessionSpec, agent_branch: BranchSpec[AgentSpec]):
    agent_spec = agent_branch.target
    agent_name = agent_branch.name
    print(f"session id: {session.uuid}")
    print(f"agent: {agent_name}")

    for message in session.messages:
        msg_agent = AgentBranchModel.objects.filter(
            owner_id=session.owner_id,
            target_id=message.agent_id,
        ).first()
        print_message(message.payload, msg_agent.name, msg_agent.target)

    async def consume_and_print(user_prompt: str):
        console.print(agent_name, style="#FFFFFF")

        stream_gen = stream_from_session(
            session,
            user_prompt,
            agent_spec=agent_spec,
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


def print_message(
    message: ModelMessage,
    name: str,
    agent: AgentSpec,
    skip_text: bool = False,
):
    content: list[tuple[str, str]] = []
    assert message.timestamp

    if not skip_text:
        content.extend(
            [
                (name, "#FFFFFF"),
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
