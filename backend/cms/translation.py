from .models import AssistantPage
from modeltranslation.translator import register, TranslationOptions

@register(AssistantPage)
class AssistansPageTranslationOptions(TranslationOptions):
    fields = (
        'title',
        'promptLabel',
        'promptButton',
        'promptPlaceholder',
        'responseLabel',
        'usageOpen',
        'usageClose',
        'usageText',
        'disclaimerOpen',
        'disclaimerClose',
        'disclaimerText',
        'copyButton',
    )
