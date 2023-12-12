from django.contrib import admin
from django.db import models

class APIKey(models.Model):
    key = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

class ChatGPTResult(models.Model):
    prompt = models.ForeignKey('Prompt', on_delete=models.CASCADE)
    result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Prompt(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

admin.site.register(Prompt)
admin.site.register(APIKey)
admin.site.register(ChatGPTResult)