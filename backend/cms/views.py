from django.http import JsonResponse, HttpResponse
from .models import AssistantPage
import logging

def assistant(request):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    try:
        content = AssistantPage.objects.get(pk=1).serialize()
    except AssistantPage.DoesNotExist:
        message = f"Content for `pk=1` does not exist"
        logging.error(message)
        return HttpResponse(message, status=404)

    return JsonResponse(content)
