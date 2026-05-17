import logging
import re

from chatddx_backend.api.models import (
    DDXCaseResult,
    DDXCaseResult_diagnoses,
    DDXTestRun,
)
from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_clients: dict[int, OpenAI] = {}


def get_openai_client(chat) -> OpenAI:
    if chat["pk"] not in _openai_clients:
        _openai_clients[chat["pk"]] = OpenAI(
            api_key=chat["api_key"],
            base_url=chat["endpoint"],
            timeout=30,
        )
        logger.debug(f"Created new client for config {chat['pk']}")

    return _openai_clients[chat["pk"]]


def invalidate_client_cache(pk: int):
    if pk in _openai_clients:
        client = _openai_clients.pop(pk)
        client.close()  # Clean up resources
        logger.debug(f"Invalidated client cache for config {pk}")


def run(run_id: int) -> int:
    chat, cases = load_env(run_id)

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
) -> int:
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

    return ddxcaseresult.pk


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
    p = re.sub(r"\b[^\s]+\b", lambda m: f'("{m.group(0)}" in s)', p)
    p = p.replace("|", " or ").replace("&", " and ")
    p = re.sub(r"\s{2,}", " ", p)
    return p


def load_env(run_id: int) -> tuple[dict, list]:
    test_run = DDXTestRun.objects.get(pk=run_id)
    serialized_chat = test_run.chat.serialize()
    serialized_chat["pk"] = test_run.chat.pk
    cases = [c.serialize() for c in test_run.group.ddxtestcase_set.all()]

    return serialized_chat, cases


def query_chat(chat: dict, case: dict) -> str:
    messages = chat["messages"] + [{"role": "user", "content": case["input"]}]

    client = get_openai_client(chat)
    completion = client.chat.completions.create(
        model=chat["model"],
        messages=messages,
    )

    return completion.choices[0].message.content
