from django.http import JsonResponse, HttpResponse
from .models import OpenAIChatCluster, OpenAIChat, PromptHistory
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import logging
import json

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
        payload = OpenAIChatCluster.objects.get(identifier=cluster).serialize()
    except OpenAIChatCluster.DoesNotExist:
        message = f"Cluster `{cluster}` does not exist"
        logging.error(message)
        return HttpResponse(message, status=404)

    return JsonResponse(payload)
