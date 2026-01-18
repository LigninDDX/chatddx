import json
import logging
import re

from openai import OpenAI, APIError, RateLimitError

from chatddx_backend.api.models import OpenAIChat, PromptHistory
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


logger = logging.getLogger(__name__)


def extract_json_from_text(text):
    try:
        match = re.search(r"```json\n?([\s\S]*?)\n?```", text)
        if match:
            return json.loads(match.group(1))

        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            return json.loads(match.group(1))

        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        return {"raw": text}


@csrf_exempt
def diagnose_symptoms(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    if request.method == "OPTIONS":
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = (
            "authorization, x-client-info, apikey, content-type"
        )
        return response

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
        symptoms = body.get("symptoms")
        chat = request.user.aiuser.config.serialize()

        if not chat["api_key"]:
            return JsonResponse({"error": "API Key is not configured"}, status=500)

        client = OpenAI(api_key=chat["api_key"], base_url=chat["endpoint"])

        logger.info(f"Processing diagnosis request for symptoms: {symptoms}")

        completion = client.chat.completions.create(
            model=chat["model"],
            messages=chat["messages"]
            + [
                {"role": "user", "content": symptoms},
            ],
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content
        logger.info("AI response received")

        diagnosis_result = extract_json_from_text(content)

        response = JsonResponse(diagnosis_result)
        response["Access-Control-Allow-Origin"] = "*"
        return response

    except RateLimitError:
        return JsonResponse(
            {"error": "För många förfrågningar. Vänta en stund och försök igen."},
            status=429,
        )
    except APIError as e:
        # Handle 402 or other API errors
        if e.code == "insufficient_quota" or (e.status_code == 402):
            return JsonResponse(
                {"error": "AI-krediter slut. Kontakta administratör."}, status=402
            )
        logger.error(f"AI API Error: {str(e)}")
        return JsonResponse({"error": f"AI gateway error: {e.status_code}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_history(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

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
        return HttpResponse(status=401)

    try:
        return JsonResponse(request.user.aiuser.config.serialize())
    except ObjectDoesNotExist:
        return HttpResponse(status=404)
