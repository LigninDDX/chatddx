from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin

from chatddx_backend.agents.models import AgentModel
from chatddx_backend.agents.models.agent import OutputTypeModel, SamplingParamsModel
from chatddx_backend.agents.trail import TrailModel

from .models import ConnectionModel


class TrailModelAdmin(ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet[TrailModel]:
        qs: QuerySet[TrailModel] = super().get_queryset(request)  # type: ignore
        return qs.filter(fingerprint="")


class ConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = ConnectionModel
        fields = "__all__"


@admin.register(ConnectionModel)
class ConnectionAdmin(TrailModelAdmin):
    form = ConnectionAdminForm
    list_display = ["name"]


class OutputTypeAdminForm(forms.ModelForm):
    class Meta:
        model = OutputTypeModel
        fields = "__all__"


@admin.register(OutputTypeModel)
class OutputTypeAdmin(TrailModelAdmin):
    form = OutputTypeAdminForm
    list_display = ["name"]


class AgentAdminForm(forms.ModelForm):
    class Meta:
        model = AgentModel
        fields = "__all__"


@admin.register(AgentModel)
class AgentAdmin(TrailModelAdmin):
    form = AgentAdminForm
    list_display = ["name"]


class SamplingParamsAdminForm(forms.ModelForm):
    class Meta:
        model = SamplingParamsModel
        fields = "__all__"


@admin.register(SamplingParamsModel)
class SamplingParamsAdmin(TrailModelAdmin):
    form = SamplingParamsAdminForm
    list_display = ["name"]
