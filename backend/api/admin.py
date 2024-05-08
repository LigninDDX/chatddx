from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from . import models


class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'config', 'user', 'prompt', 'response']


class AIUserInline(admin.StackedInline):
    model = models.AIUser
    verbose_name_plural = "AI Users"


class UserAdmin(BaseUserAdmin):
    inlines = [AIUserInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(models.OpenAIChatCluster)
admin.site.register(models.OpenAIChat)
admin.site.register(models.OpenAIMessage)
admin.site.register(models.OpenAIMessageRole)
admin.site.register(models.OpenAIModel)
admin.site.register(models.OpenAILogitBias)
admin.site.register(models.PromptHistory, PromptHistoryAdmin)
