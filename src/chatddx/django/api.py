from typing import List

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

from chatddx.repo.shufflers.main import (
    load_agents,
    load_agents_async,
    load_branch_async,
)
from chatddx.runtime.runners import run_from_spec

api = NinjaAPI(title="ChatDDx Swift API", version="1.0.0")
User = get_user_model()


class SwiftDiagnoseRequest(Schema):
    symptoms: str
    model: str


class ModelOptionResponse(Schema):
    value: str
    label: str


def get_authenticated_username(request: HttpRequest) -> str | None:
    if not request.user or request.user.is_anonymous:
        return None
    return request.user.username


@api.get("/agents", response=List[ModelOptionResponse])
async def get_agents_endpoint(request: HttpRequest, output_type: str = None):
    username = await sync_to_async(get_authenticated_username)(request)

    if username is None:
        return api.create_response(
            request,
            {"error": "Authentication required."},
            status=401,
        )

    try:
        agents = await load_agents_async(owner_name=username, output_type=output_type)

        options = [
            {"value": agent.name, "label": f"{agent.name.capitalize()} Agent"}
            for agent in agents
        ]

        return options

    except Exception as e:
        return api.create_response(
            request,
            {"error": f"Failed to load agent configurations. Detail: {e}"},
            status=500,
        )


@api.post("/diagnose")
async def swift_diagnose_endpoint(request: HttpRequest, payload: SwiftDiagnoseRequest):
    username = await sync_to_async(get_authenticated_username)(request)

    if username is None:
        return api.create_response(
            request,
            {
                "error": "Authentication required. Your session cookie was missing or expired."
            },
            status=401,
        )

    try:
        agent = await load_branch_async(
            bundle_name="agent",
            owner_name=username,
            branch_name=payload.model,
        )

        if not agent:
            raise ValueError(f"No configuration branch found named '{payload.model}'")

        agent_spec = agent.target

    except Exception as e:
        return api.create_response(
            request,
            {
                "error": f"could not load model '{payload.model}' found registered for user '{username}'. Detail: {e}"
            },
            status=400,
        )

    run_result = await run_from_spec(agent_spec=agent_spec, prompt=payload.symptoms)

    return run_result.output
