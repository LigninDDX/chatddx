from django.db import models
from django.utils.translation import gettext_lazy as _
from django.forms.models import model_to_dict 
import markdown2

class AssistantPage(models.Model):
    class Meta:
        verbose_name_plural = "Assistant page"

    title = models.CharField(max_length=255)
    promptLabel = models.CharField(max_length=255)
    promptPlaceholder = models.CharField(max_length=255)
    promptButton = models.CharField(max_length=255)
    responseLabel = models.CharField(max_length=255)
    usageOpen = models.CharField(max_length=255)
    usageClose = models.CharField(max_length=255)
    usageText = models.TextField()
    disclaimerOpen = models.CharField(max_length=255)
    disclaimerClose = models.CharField(max_length=255)
    disclaimerText = models.TextField()
    copyButton = models.CharField(max_length=255)
    def __str__(self):
        return str(self.title)

    def serialize(self):
        data = model_to_dict(self, fields=[field.name for field in self._meta.fields])
        data["disclaimerText"] = markdown2.markdown(data["disclaimerText"])
        data["usageText"] = markdown2.markdown(data["usageText"])
        return data

