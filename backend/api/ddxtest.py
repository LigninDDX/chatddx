import logging
import re

from api.models import (
    DDXCaseResult,
    DDXCaseResult_diagnoses,
    DDXTestCase,
    DDXTestGroup,
    DDXTestRun,
    Diagnosis,
    OpenAIChat,
)
from openai import OpenAI

logger = logging.getLogger(__name__)


def run(group_name: str, chat_identifier: str) -> DDXTestRun:
    test_run = load_env(group_name, chat_identifier)
    chat = test_run.chat.serialize()

    client = OpenAI(
        api_key=chat["api_key"],
        base_url=chat["endpoint"],
    )

    for case in test_run.group.ddxtestcase_set.all():
        logger.info(case)
        response = query_chat(client, chat, case)
        result = evaluate_response(case, response)
        logger.info(result)
        save_test_result(test_run, case, response, result)

    return test_run


def save_test_result(
    test_run: DDXTestRun, case: DDXTestCase, response: str, results: tuple[int, str]
) -> DDXCaseResult:
    ddxcaseresult = DDXCaseResult.objects.create(
        run=test_run,
        case=case,
        response=response,
    )

    DDXCaseResult_diagnoses.objects.bulk_create(
        [
            DDXCaseResult_diagnoses(
                ddxcaseresult=ddxcaseresult,
                diagnosis=diagnosis,
                rank=rank,
            )
            for diagnosis, rank in results
        ]
    )

    return ddxcaseresult


def evaluate_response(case: DDXTestCase, response: str) -> tuple[Diagnosis, int]:
    suggestions = [
        re.sub(r"^\d+\.\s*", "", s).strip().lower()
        for s in response.strip().split("\n")
    ]

    def match(p):
        # shut up eval is safe and needed here
        return next(
            (i + 1 for i, s in enumerate(suggestions) if eval(p, {"s": s})),
            0,
        )

    return [(d, match(render_pattern(d.pattern))) for d in case.diagnoses.all()]


def render_pattern(p: str) -> str:
    # A simplified pattern matching for identifying diagnoses in plain text
    # example pattern: "diverticulitis | (((gastro & intestinal) | gi) & inflammation)"
    # string in the pattern are quoted and compared with "in s" which is a source string
    # made available by closure.
    p = re.sub(r"\b[a-zA-Z]+\b", lambda m: f'("{m.group(0)}" in s)', p)
    p = p.replace("|", " or ").replace("&", " and ")
    p = re.sub(r"\s{2,}", " ", p)
    return p


def load_env(group_name: str, chat_identifier: str) -> DDXTestRun:
    try:
        group = DDXTestGroup.objects.get(name=group_name)
    except DDXTestGroup.DoesNotExist:
        raise Exception(
            f"Group '{group_name}' does not exist: {DDXTestGroup.objects.values_list('name', flat=True)}"
        )

    try:
        chat = OpenAIChat.objects.get(identifier=chat_identifier)
    except OpenAIChat.DoesNotExist:
        raise Exception(
            f"Chat '{chat_identifier}' does not exist: {OpenAIChat.objects.values_list('identifier', flat=True)}"
        )

    return DDXTestRun.objects.create(group=group, chat=chat)


def query_chat(client: OpenAI, chat: dict, case: DDXTestCase) -> str:
    messages = chat["messages"] + [{"role": "user", "content": case.input}]

    completion = client.chat.completions.create(
        model=chat["model"],
        messages=messages,
    )

    return completion.choices[0].message.content
