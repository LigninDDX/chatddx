from django.contrib import admin
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class OpenAIMessageRole(models.Model):
    class Meta:
        verbose_name_plural = "OpenAI Message Roles"

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class OpenAIModel(models.Model):
    class Meta:
        verbose_name_plural = "OpenAI Models"

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class OpenAILogitBias(models.Model):
    class Meta:
        verbose_name_plural = "OpenAI Logit Biases"

    token = models.CharField(max_length=255)
    bias = models.IntegerField(
            validators=[
                MaxValueValidator(100),
                MinValueValidator(-100),
                ])

class OpenAIMessage(models.Model):
    class Meta:
        verbose_name_plural = "OpenAI Messages"

    description = models.CharField(
            default="",
            max_length=255,
            )
    content = models.TextField()
    role = models.ForeignKey(OpenAIMessageRole, on_delete=models.PROTECT)
    name = models.CharField(
            max_length=255,
            default=None,
            null=True,
            blank=True,
            )

    def __str__(self):
        return self.description

class OpenAIChat(models.Model):
    class Meta:
        verbose_name_plural = "OpenAI Chat Configuration"

    def __str__(self):
        return self.description

    description = models.CharField(
            max_length=255,
            default="",
            )
    active = models.BooleanField(default=True)
    endpoint = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    messages = models.ManyToManyField(OpenAIMessage)
    model = models.ForeignKey(OpenAIModel, on_delete=models.PROTECT)

    frequency_penalty = models.FloatField(
            default=0,
            validators=[
                MinValueValidator(-2),
                MaxValueValidator(2),
                ])

    logit_bias = models.ForeignKey(
            OpenAILogitBias,
            on_delete=models.PROTECT,
            null=True,
            default=None,
            blank=True,
            )

    max_tokens = models.IntegerField(
            validators=[
                MinValueValidator(1),
                MaxValueValidator(2000),
                ])

    presence_penalty = models.FloatField(
            default=0,
            validators=[
                MinValueValidator(-2),
                MaxValueValidator(2),
                ])

    temperature = models.FloatField(
            default=1,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(2),
                ]
            )

    top_p = models.FloatField(
            default=1,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1),
                ]
            )

    user = models.CharField(
            max_length=255,
            default=None,
            blank=True,
            null=True,
            )

class APIKey(models.Model):
    key = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

class ChatGPTResult(models.Model):
    prompt = models.ForeignKey('Prompt', on_delete=models.CASCADE)
    result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Prompt(models.Model):
    role = models.TextField(default="")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

admin.site.register(Prompt)
admin.site.register(APIKey)
admin.site.register(ChatGPTResult)

admin.site.register(OpenAILogitBias)
admin.site.register(OpenAIChat)
admin.site.register(OpenAIModel)
admin.site.register(OpenAIMessage)
admin.site.register(OpenAIMessageRole)
