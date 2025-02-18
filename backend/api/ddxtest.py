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

_openai_client = None


def get_openai_client(chat):
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=chat["api_key"],
            base_url=chat["endpoint"],
        )

    return _openai_client


def run(group_name: str, chat_identifier: str) -> int:
    run_id, chat, cases = load_env(group_name, chat_identifier)

    for case in cases:
        run_case(run_id, chat, case)

    return run_id


def run_case(run_id, chat, case):
    logger.info(case)
    response = query_chat(chat, case)
    results = evaluate_response(case, response)
    logger.info(results)
    return save_test_results(run_id, case, response, results)


def save_test_results(
    run_id: int, case: dict, response: str, results: list[tuple[int, int]]
) -> DDXCaseResult:
    ddxcaseresult = DDXCaseResult.objects.create(
        run_id=run_id,
        case_id=case["pk"],
        response=response,
    )

    DDXCaseResult_diagnoses.objects.bulk_create(
        [
            DDXCaseResult_diagnoses(
                ddxcaseresult=ddxcaseresult,
                diagnosis_id=diagnosis_pk,
                rank=rank,
            )
            for diagnosis_pk, rank in results
        ]
    )

    return ddxcaseresult


def evaluate_response(case: dict, response: str) -> list[tuple[int, int]]:
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

    return [(d["pk"], match(render_pattern(d["pattern"]))) for d in case["diagnoses"]]


def render_pattern(p: str) -> str:
    # A simplified pattern matching for identifying diagnoses in plain text
    # example pattern: "diverticulitis | (((gastro & intestinal) | gi) & inflammation)"
    # string in the pattern are quoted and compared with "in s" which is a source string
    # made available by closure.
    p = re.sub(r"\b[a-zA-Z]+\b", lambda m: f'("{m.group(0)}" in s)', p)
    p = p.replace("|", " or ").replace("&", " and ")
    p = re.sub(r"\s{2,}", " ", p)
    return p


def load_env(group_name: str, chat_identifier: str) -> int:
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

    test_run = DDXTestRun.objects.create(group=group, chat=chat)
    serialized_chat = test_run.chat.serialize()
    cases = [c.serialize() for c in test_run.group.ddxtestcase_set.all()]

    return test_run.pk, serialized_chat, cases


def query_chat(chat: dict, case: dict) -> str:
    messages = chat["messages"] + [{"role": "user", "content": case["input"]}]

    client = get_openai_client(chat)
    completion = client.chat.completions.create(
        model=chat["model"],
        messages=messages,
    )

    return completion.choices[0].message.content
