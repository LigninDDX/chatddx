import asyncio

from django.core.management.base import BaseCommand, CommandError
from rich.console import Console
from rich.live import Live
from rich.pretty import Pretty

from chatddx_backend.agents.models import Agent
from chatddx_backend.agents.runtime import run_stream


class Command(BaseCommand):
    help = "Passes a prompt to an agent"

    def add_arguments(self, parser):
        parser.add_argument("agent", type=str, help="Name of the agent to use")
        parser.add_argument("prompt", type=str, help="Prompt to send to the agent")

    def handle(self, *args, **options):
        prompt = options.get("prompt")
        agent = Agent.objects.select_related(
            "connection",
            "config",
            "schema",
        ).get(name=options.get("agent"))

        if prompt is None:
            raise CommandError(f"Error: No prompt")

        asyncio.run(run_stream_cli_live(agent, prompt))


async def run_stream_cli_print(agent, prompt):
    async for data in run_stream(agent, prompt):
        print(data, flush=True)


async def run_stream_cli_live(agent, prompt):
    console = Console()

    with Live("", console=console) as live:
        live.update("Requesting data...")
        async for data in run_stream(agent, prompt):
            live.update(Pretty(data))
