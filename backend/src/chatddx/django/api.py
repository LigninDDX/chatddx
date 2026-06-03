# src/chatddx/django/api.py
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

from chatddx.repo.shufflers.main import load_branch_async
from chatddx.runtime.runners import run_from_spec

api = NinjaAPI(title="ChatDDx Swift API", version="1.0.0")
User = get_user_model()


class SwiftDiagnoseRequest(Schema):
    symptoms: str
    model: str


@api.post("/diagnose")
async def swift_diagnose_endpoint(request: HttpRequest, payload: SwiftDiagnoseRequest):

    try:
        username = request.user.username
        agent = await load_branch_async(
            bundle_name="agent",
            owner_name=username,
            branch_name=payload.model,
        )
        agent_spec = agent.target
    except Exception as e:
        return api.create_response(
            request,
            {
                "error": f"could not load model '{payload.model}' found registered for user '{username}'. {e}"
            },
            status=400,
        )

    run_result = await run_from_spec(agent_spec=agent_spec, prompt=payload.symptoms)

    return run_result.output
