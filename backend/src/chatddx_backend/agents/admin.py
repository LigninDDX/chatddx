from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Connection


class ConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = Connection
        fields = "__all__"


@admin.register(Connection)
class ConnectionAdmin(ModelAdmin):
    form = ConnectionAdminForm
    list_display = ["name"]
