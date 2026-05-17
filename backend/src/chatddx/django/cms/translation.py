from chatddx_backend.cms.models import AssistantPage
from modeltranslation.translator import TranslationOptions, register


@register(AssistantPage)
class AssistansPageTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "promptLabel",
        "promptButton",
        "promptPlaceholder",
        "responseLabel",
        "usageOpen",
        "usageClose",
        "usageText",
        "disclaimerOpen",
        "disclaimerClose",
        "disclaimerText",
        "copyButton",
    )
