from django.contrib import admin
from . import models

class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'config', 'user', 'prompt', 'response']

admin.site.register(models.OpenAIChatCluster)
admin.site.register(models.OpenAIChat)
admin.site.register(models.OpenAIMessage)
admin.site.register(models.OpenAIMessageRole)
admin.site.register(models.OpenAIModel)
admin.site.register(models.OpenAILogitBias)
admin.site.register(models.PromptHistory, PromptHistoryAdmin)
