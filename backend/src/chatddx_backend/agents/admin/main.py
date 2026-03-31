# src/chatddx_backend/agents/admin/history.py
from dataclasses import asdict
from typing import Any

from django.contrib import admin
from django.db.models import Max, Min
from django.forms import ModelForm
from django.http import HttpRequest
from django.utils.formats import date_format
from django_json_widget.widgets import JSONEditorWidget

from chatddx_backend.agents.admin import agent, history
from chatddx_backend.agents.admin.base import TrailModelAdmin, TypedModelAdmin
from chatddx_backend.agents.admin.utils import get_step_nav


class ConnectionAdminForm(ModelForm):
    class Meta:
        model = agent.Connection
        fields = "__all__"


@admin.register(agent.Connection)
class ConnectionAdmin(TrailModelAdmin[agent.Connection]):
    form = ConnectionAdminForm
    list_display = ["name"]


class OutputTypeAdminForm(ModelForm):
    class Meta:
        model = agent.OutputType
        fields = "__all__"


@admin.register(agent.OutputType)
class OutputTypeAdmin(TrailModelAdmin[agent.OutputType]):
    form = OutputTypeAdminForm
    list_display = ["name"]


class AgentAdminForm(ModelForm):
    class Meta:
        model = agent.Agent
        fields = "__all__"


@admin.register(agent.Agent)
class AgentAdmin(TrailModelAdmin[agent.Agent]):
    form = AgentAdminForm
    list_display = ["name"]


class SamplingParamsAdminForm(ModelForm):
    class Meta:
        model = agent.SamplingParams
        fields = "__all__"


@admin.register(agent.SamplingParams)
class SamplingParamsAdmin(TrailModelAdmin[agent.SamplingParams]):
    form = SamplingParamsAdminForm
    list_display = ["name"]


class IdentityForm(ModelForm):
    class Meta:
        model = history.Identity
        fields = "__all__"
        widgets = {"secrets": JSONEditorWidget}


@admin.register(history.Identity)
class IdentityAdmin(TypedModelAdmin[history.Identity]):
    form = IdentityForm
    list_display = [
        "name",
        "auth_user",
        "guest_id",
    ]
    fields = list_display + [
        "secrets",
    ]
    readonly_fields = ["guest_id"]


@admin.register(history.Session)
class SessionAdmin(TypedModelAdmin[history.Session]):
    list_display = [
        "timestamp",
        "uuid_",
        "description",
        "earliest_message",
        "latest_message",
        "default_agent",
        "message_count",
    ]
    fields = list_display + []
    readonly_fields = fields

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.annotate(
            annotated_earliest=Min("messages__timestamp"),
            annotated_latest=Max("messages__timestamp"),
        )

    @admin.display(description="UUID")
    def uuid_(self, session_model: history.Session):
        return session_model.uuid

    @admin.display(
        description="Earliest Message",
        ordering="annotated_earliest",
    )
    def earliest_message(self, session_model: history.Session):
        timestamp = getattr(session_model, "annotated_earliest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None

    @admin.display(
        description="Latest Message",
        ordering="annotated_latest",
    )
    def latest_message(self, session_model: history.Session):
        timestamp = getattr(session_model, "annotated_latest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None


@admin.register(history.Message)
class MessageAdmin(TypedModelAdmin[history.Message]):
    list_display = [
        "timestamp",
        "__str__",
        "get_session",
        "direction",
        "role",
        "agent",
    ]
    fields = list_display + [
        "run_id",
        "markdown",
        "payload",
    ]

    readonly_fields = fields

    show_add_link = False
    compressed_fields = True

    @admin.display(description="Session", ordering="session__id")
    def get_session(self, obj: history.Message):
        return history.Session.objects.get(pk=obj.session.pk)

    def has_add_permission(self, request: HttpRequest):
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: history.Message | None = None,
    ):
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: history.Message | None = None,
    ):
        return False

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ):
        extra_context = extra_context or {}

        qs = self.get_queryset(request)

        message_model = qs.get(pk=object_id)
        qs_session = qs.filter(session_id=message_model.spec.session_id)

        step_nav = get_step_nav(message_model, qs_session)

        extra_context |= asdict(step_nav)

        return super().change_view(request, object_id, form_url, extra_context)
