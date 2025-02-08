import re

from api.models import DDXTestGroup, DDXTestResult, DDXTestRun
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI
from thefuzz import fuzz

clients = {}
chats = {}


def get_chat(chat):
    key = chat.identifier
    if key in chats:
        return chats[key]
    chats[key] = chat.serialize()
    return chats[key]


def get_client(chat):
    key = chat.identifier
    if key in clients:
        return clients[key]

    clients[key] = OpenAI(
        api_key=chat.api_key,
        base_url=chat.endpoint,
    )
    return clients[key]


class Command(BaseCommand):
    help = "Run a test group and produce a report"

    def add_arguments(self, parser):
        parser.add_argument("group", type=str)

    def handle(self, *args, **options):
        group_name = options["group"]
        try:
            group = DDXTestGroup.objects.get(name=group_name)
            self.stdout.write(f"Testing '{group_name}'...")
        except DDXTestGroup.DoesNotExist:
            raise CommandError(f"Group '{group_name}' does not exist")

        tests = group.ddxtest_set.all()
        run = DDXTestRun.objects.create(group=group)

        for test in tests:
            expects = re.split(r"[;,\n]", test.expect.strip())
            for chat in test.chats.all():
                print(f"{test}:{chat}")
                client = get_client(chat)
                schat = get_chat(chat)
                messages = schat["messages"] + [{"role": "user", "content": test.input}]
                print(messages)
                completion = client.chat.completions.create(
                    model=schat["model"],
                    messages=messages,
                )
                output = completion.choices[0].message.content.strip()
                suggestions = output.split("\n")
                saved = False
                for rank, suggestion in enumerate(suggestions):
                    ratio = 0

                    for expect in expects:
                        ratio = max(
                            ratio,
                            fuzz.ratio(
                                re.sub(r"^\d+\.\s*", "", suggestion).strip().lower(),
                                expect.strip().lower(),
                            ),
                        )
                        print(
                            f"{rank + 1}: '{suggestion}' is {ratio} from expected '{expect}'."
                        )

                    if ratio > 75:
                        DDXTestResult.objects.create(
                            run=run,
                            test=test,
                            chat=chat,
                            output=output,
                            expect_pos=rank + 1,
                        )
                        saved = True
                        break
                if not saved:
                    DDXTestResult.objects.create(
                        run=run, test=test, chat=chat, output=output, expect_pos=0
                    )
