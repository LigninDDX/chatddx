# src/chatddx_backend/agents/admin/history.py
import json
from dataclasses import asdict
from typing import Any

from django.contrib import admin
from django.db.models import Max, Min
from django.http import HttpRequest
from django.utils.formats import date_format
from markdown import markdown
from unfold.admin import mark_safe
from unfold.utils import format_html

from chatddx_backend.agents.admin import forms, proxies
from chatddx_backend.agents.admin.base import TrailModelAdmin, TypedModelAdmin
from chatddx_backend.agents.admin.utils import (
    get_step_nav,
    truncate_content,
)


@admin.register(proxies.Agent)
class AgentAdmin(TrailModelAdmin[proxies.Agent]):
    form = forms.AgentForm
    list_display = [
        "__str__",
        "connection",
        "sampling_params",
        "output_type",
        "validation_strategy",
        "coercion_strategy",
        "tool_group",
    ]


@admin.register(proxies.Connection)
class ConnectionAdmin(TrailModelAdmin[proxies.Connection]):
    form = forms.ConnectionForm
    list_display = ["name"]


@admin.register(proxies.OutputType)
class OutputTypeAdmin(TrailModelAdmin[proxies.OutputType]):
    form = forms.OutputTypeForm
    list_display = ["name"]


@admin.register(proxies.SamplingParams)
class SamplingParamsAdmin(TrailModelAdmin[proxies.SamplingParams]):
    form = forms.SamplingParamsForm
    list_display = ["name"]


@admin.register(proxies.ToolGroup)
class ToolGroupAdmin(TrailModelAdmin[proxies.ToolGroup]):
    form = forms.ToolGroupForm
    list_display = ["name"]


@admin.register(proxies.Identity)
class IdentityAdmin(TypedModelAdmin[proxies.Identity]):
    form = forms.IdentityForm
    list_display = [
        "name",
        "auth_user",
        "guest_id",
    ]
    fields = list_display + [
        "secrets",
    ]
    readonly_fields = ["guest_id"]


@admin.register(proxies.Session)
class SessionAdmin(TypedModelAdmin[proxies.Session]):
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
    def uuid_(self, session_model: proxies.Session):
        return session_model.uuid

    @admin.display(
        description="Earliest Message",
        ordering="annotated_earliest",
    )
    def earliest_message(self, session_model: proxies.Session):
        timestamp = getattr(session_model, "annotated_earliest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None

    @admin.display(
        description="Latest Message",
        ordering="annotated_latest",
    )
    def latest_message(self, session_model: proxies.Session):
        timestamp = getattr(session_model, "annotated_latest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None


@admin.register(proxies.Message)
class MessageAdmin(TypedModelAdmin[proxies.Message]):
    list_display = [
        "timestamp",
        "role",
        "content_short",
        "direction",
        "agent",
    ]
    fields = list_display + [
        "run_id",
        "get_session",
        "thinking",
        "content",
        "payload",
    ]

    readonly_fields = fields

    show_add_link = False
    compressed_fields = True

    @admin.display(description="Session", ordering="session__id")
    def get_session(self, message: proxies.Message):
        return proxies.Session.objects.get(pk=message.session.pk)

    def content_short(self, message: proxies.Message):
        return truncate_content(message.content, 55)

    @admin.display(description="Content")
    def content(self, message: proxies.Message):
        json_data_tpl = (
            '<div class="highlight">'
            '<pre class="white-space: pre-wrap; word-wrap: break-word;; line-height: 125%;">{}</pre>'
            "</div>"
        )
        markdown_tpl = '<div class="prose dark:prose-invert max-w-none">{}</div>'

        match message.typed_content:
            case None:
                return ""
            case str():
                html = markdown(
                    message.typed_content,
                    extensions=["fenced_code", "tables"],
                )
                return format_html(markdown_tpl, mark_safe(html))
            case _:
                json_data = json.dumps(message.typed_content, indent=4)
                return format_html(json_data_tpl, json_data)

    def has_add_permission(self, request: HttpRequest):
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: proxies.Message | None = None,
    ):
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: proxies.Message | None = None,
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
