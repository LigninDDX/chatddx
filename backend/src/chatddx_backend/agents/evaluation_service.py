import logging
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

from chatddx_backend.api.models import (
    DDXCaseResult,
    DDXCaseResult_diagnoses,
    DDXTestRun,
)

from .models_ai import DDXResponse

logger = logging.getLogger(__name__)


def run(run_id: int) -> int:
    test_run = DDXTestRun.objects.select_related("chat", "group").get(pk=run_id)
    agent_profile = test_run.chat
    test_cases = test_run.group.ddxtestcase_set.all().prefetch_related("diagnoses")

    # 2. Setup the Pydantic-AI Agent
    # We map your Django 'endpoint' and 'api_key' to the Pydantic-AI Model
    model = OpenAIChatModel(
        agent_profile.model.name,
        base_url=agent_profile.endpoint,
        api_key=agent_profile.api_key,
    )

    agent = Agent(
        model,
        result_type=DDXResponse,  # This replaces evaluate_response() logic
        retries=2,
    )

    # 3. Define System Prompts from DB
    @agent.system_prompt
    def get_system_instructions() -> str:
        # Replaces your manual message list building
        messages = agent_profile.messages.all().order_by("openaichat_messages__order")
        return "\n\n".join([m.content for m in messages])

    # 4. Execute Loop
    for case in test_cases:
        # Run sync or async depending on your worker setup
        result = agent.run_sync(
            case.input,
            model_settings={
                "temperature": agent_profile.temperature,
                "max_tokens": agent_profile.max_tokens,
            },
        )

        save_test_results(test_run.pk, case, result.data)

    return run_id


def save_test_results(run_id: int, case, ai_data: DDXResponse) -> int:
    """
    Saves the structured AI output directly to the legacy tables.
    """
    # Create the master result record
    ddxcaseresult = DDXCaseResult.objects.create(
        run_id=run_id,
        case_id=case.pk,
        response=str(ai_data.model_dump_json()),  # Store JSON for audit
    )

    # Replaces the rank/match logic
    new_ranks = []
    for rank, item in enumerate(ai_data.diagnoses, start=1):
        # We try to match the AI name to your Diagnosis table
        # In a real scenario, you'd use a vector search or slug match here
        from chatddx_backend.api.models import Diagnosis

        diag = Diagnosis.objects.filter(name__iexact=item.name).first()

        if diag:
            new_ranks.append(
                DDXCaseResult_diagnoses(
                    ddxcaseresult=ddxcaseresult, diagnosis=diag, rank=rank
                )
            )

    DDXCaseResult_diagnoses.objects.bulk_create(new_ranks)
    return ddxcaseresult.pk
