from django.http import JsonResponse, HttpResponse
from .models import OpenAIChatCluster, OpenAIChat, PromptHistory
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import logging
import json
from django.core.exceptions import ObjectDoesNotExist

@csrf_exempt
@require_http_methods(["POST"])
def chat_history(request):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    data = json.loads(request.body)

    result = PromptHistory.objects.create(
        user = request.user,
        config = OpenAIChat.objects.get(identifier=data["config"]),
        prompt = data["prompt"],
        response = data["response"],
    )

    return JsonResponse({"success": "true"})

def chat_cluster(request, cluster):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    try:
        return JsonResponse(request.user.aiuser.config.serialize())
    except ObjectDoesNotExist:
        return HttpResponse("Not Found", status=404)
