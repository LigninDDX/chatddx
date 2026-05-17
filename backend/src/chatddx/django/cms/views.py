import logging

from chatddx_backend.cms.models import AssistantPage
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import translation


def assistant(request):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    try:
        content = AssistantPage.objects.get(pk=1).serialize()
    except AssistantPage.DoesNotExist:
        message = f"Content for `pk=1` does not exist"
        logging.error(message)
        return HttpResponse(message, status=404)

    content["languages"] = settings.LANGUAGES
    content["lang"] = translation.get_language()

    return JsonResponse(content)
