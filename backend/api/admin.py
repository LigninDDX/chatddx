from django.contrib import admin
from . import models

admin.site.register(models.OpenAIChatCluster)
admin.site.register(models.OpenAIChat)
admin.site.register(models.OpenAIMessage)
admin.site.register(models.OpenAIMessageRole)
admin.site.register(models.OpenAIModel)
admin.site.register(models.OpenAILogitBias)
admin.site.register(models.PromptHistory)
