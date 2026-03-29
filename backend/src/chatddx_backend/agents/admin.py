from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ConnectionModel


class ConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = ConnectionModel
        fields = "__all__"


@admin.register(ConnectionModel)
class ConnectionAdmin(ModelAdmin):
    form = ConnectionAdminForm
    list_display = ["name"]
