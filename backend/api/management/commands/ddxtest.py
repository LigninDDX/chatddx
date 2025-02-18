from api import ddxtest
from api.tasks import ddxtest_task
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a test group and produce a report"

    def add_arguments(self, parser):
        parser.add_argument("group", type=str)
        parser.add_argument("chat", type=str)
        parser.add_argument(
            "--worker", action="store_true", help="Run in a worker thread"
        )

    def handle(self, *args, **options):
        group = options["group"]
        chat = options["chat"]
        if options["worker"]:
            ddxtest_task.delay(group, chat)
        else:
            ddxtest.run(group, chat)
