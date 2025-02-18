from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin

from . import models


@admin.register(models.AssistantPage)
class AssistantPageAdmin(ModelAdmin, TabbedTranslationAdmin):
    pass
