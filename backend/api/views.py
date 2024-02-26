from django.http import JsonResponse, HttpResponse
from .models import OpenAIChatCluster
import logging


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
