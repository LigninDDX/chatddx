import json
import logging

from chatddx_backend.api.models import OpenAIChat, OpenAIChatCluster, PromptHistory
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def chat_history(request):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    data = json.loads(request.body)

    result = PromptHistory.objects.create(
        user=request.user,
        config=OpenAIChat.objects.get(identifier=data["config"]),
        prompt=data["prompt"],
        response=data["response"],
    )

    return JsonResponse({"success": "true"})


def chat_cluster(request, cluster):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    try:
        return JsonResponse(request.user.aiuser.config.serialize())
    except ObjectDoesNotExist:
        return HttpResponse("Not Found", status=404)
