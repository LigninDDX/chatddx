from api import ddxtest
from api.models import DDXTestGroup, DDXTestRun, OpenAIChat
from api.tasks import ddxtest_task
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a test run and run it sync or with a worker"

    def add_arguments(self, parser):
        parser.add_argument("group", type=str)
        parser.add_argument("chat", type=str)
        parser.add_argument(
            "--worker", action="store_true", help="Run in a worker thread"
        )

    def handle(self, **options):
        group_name = options["group"]
        chat_identifier = options["chat"]
        try:
            group = DDXTestGroup.objects.get(name=group_name)
        except DDXTestGroup.DoesNotExist:
            raise CommandError(
                f"Group '{group_name}' does not exist: {DDXTestGroup.objects.values_list('name', flat=True)}"
            )

        try:
            chat = OpenAIChat.objects.get(identifier=chat_identifier)
        except OpenAIChat.DoesNotExist:
            raise CommandError(
                f"Chat '{chat_identifier}' does not exist: {OpenAIChat.objects.values_list('identifier', flat=True)}"
            )

        test_run = DDXTestRun.objects.create(group=group, chat=chat)

        if options["worker"]:
            ddxtest_task.delay(test_run.pk)
        else:
            ddxtest.run(test_run.pk)
