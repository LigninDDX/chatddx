from chatddx_backend.cms import models
from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin


@admin.register(models.AssistantPage)
class AssistantPageAdmin(ModelAdmin, TabbedTranslationAdmin):
    pass
