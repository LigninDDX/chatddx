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

from chatddx.core.proxies import Identity
from chatddx.django.portal.admin.base import TypedModelAdmin
from chatddx.history.proxies import Message, Session
from chatddx.utils import get_step_nav, truncate_content


@admin.register(Identity)
class IdentityAdmin(TypedModelAdmin[Identity]):
    list_display = [
        "name",
        "auth_user",
        "guest_id",
    ]
    fields = list_display + [
        "secrets",
    ]
    readonly_fields = ["guest_id"]


@admin.register(Session)
class SessionAdmin(TypedModelAdmin[Session]):
    list_display = [
        "timestamp",
        "uuid_",
        "description",
        "latest_message",
        "default_agent_",
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

    @admin.display(description="Default agent")
    def default_agent_(self, session_model: Session):
        return session_model.default_agent.name if session_model.default_agent else "-"

    @admin.display(description="UUID")
    def uuid_(self, session_model: Session):
        return session_model.uuid

    @admin.display(
        description="Earliest Message",
        ordering="annotated_earliest",
    )
    def earliest_message(self, session_model: Session):
        timestamp = getattr(session_model, "annotated_earliest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None

    @admin.display(
        description="Latest Message",
        ordering="annotated_latest",
    )
    def latest_message(self, session_model: Session):
        timestamp = getattr(session_model, "annotated_latest", None)
        if timestamp:
            return date_format(timestamp, "DATETIME_FORMAT")
        return None


@admin.register(Message)
class MessageAdmin(TypedModelAdmin[Message]):
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
    def get_session(self, message: Message):
        return Session.objects.get(pk=message.session.pk)

    def content_short(self, message: Message):
        return truncate_content(message.content, 55)  # type: ignore

    @admin.display(description="Content")
    def content(self, message: Message):
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
        obj: Message | None = None,
    ):
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Message | None = None,
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

        step_nav = get_step_nav(message_model, qs_session)  # pyright: ignore[reportArgumentType]

        extra_context |= asdict(step_nav)

        return super().change_view(request, object_id, form_url, extra_context)
