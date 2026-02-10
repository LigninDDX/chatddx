from chatddx_backend.api import evaluation_service
from chatddx_backend.api.models import EvalDataset, EvalRun, AgentProfile
from chatddx_backend.api.tasks import run_evaluation_task
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Dispatch an evaluation run for a specific Agent against a Dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "agent_identifier", type=str, help="The AI Agent configuration to use"
        )
        parser.add_argument(
            "dataset_name", type=str, help="The set of test cases to run"
        )
        parser.add_argument("--sync", action="store_true", help="Force synchronous run")

    def handle(self, **options):
        dataset_name = options["dataset_name"]
        agent_id = options["agent_identifier"]

        try:
            agent_profile = AgentProfile.objects.get(identifier=agent_id)
        except AgentProfile.DoesNotExist:
            raise CommandError(f"Agent Profile '{agent_id}' not found.")

        try:
            dataset = EvalDataset.objects.get(name=dataset_name)
        except EvalDataset.DoesNotExist:
            raise CommandError(f"Dataset '{dataset_name}' not found.")

        eval_run = EvalRun.objects.create(dataset=dataset, agent=agent_profile)

        self.stdout.write(f"Created evaluation run ID: {eval_run.pk}")

        if options["sync"]:
            evaluation_service.execute_run(eval_run.pk)
            self.stdout.write("Run completed synchronously.")
        else:
            run_evaluation_task.delay(eval_run.pk)
            self.stdout.write("Task dispatched to worker.")
