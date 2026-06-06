import json
from dataclasses import asdict
from typing import Any

from django.contrib import admin
from django.db.models import Max, Min, OuterRef, QuerySet, Subquery
from django.http import HttpRequest
from django.urls import reverse
from django.utils.formats import date_format
from markdown import markdown
from unfold.admin import mark_safe
from unfold.utils import format_html

from chatddx.core.proxies import Identity
from chatddx.django.portal.admin.base import TypedModelAdmin
from chatddx.history.proxies import Message, Session
from chatddx.repo.proxies import Agent
from chatddx.repo.shufflers.main import load_agent
from chatddx.utils import get_step_nav, truncate_content


def get_agent_link(msg: Message):
    url = (
        reverse(
            f"admin:orm_superagent_change",
            args=[msg.agent_branch_id],
        )
        + f"?from_message={msg.pk}"
    )
    label = f"{msg.agent_branch_name} ({msg.agent.fingerprint[:6]})"

    return format_html('<a href="{}">{}</a>', url, label)


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

        return (
            qs.filter(
                owner__name=request.user.username,
            )
            .annotate(
                annotated_earliest=Min("messages__timestamp"),
                annotated_latest=Max("messages__timestamp"),
            )
            .order_by("-timestamp")
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
    change_form_template = "admin/agents/message/change_form.html"
    add_form_template = "admin/agents/message/change_form.html"
    list_display = [
        "timestamp",
        "role",
        "content_short",
        "direction",
        "agent_",
    ]
    fields = list_display + [
        "run_id",
        "get_session",
        "thinking",
        "content",
        "payload",
    ]

    ordering = ("-timestamp",)
    readonly_fields = fields

    show_add_link = False
    compressed_fields = True

    def agent_(self, obj):
        return get_agent_link(obj)

    def get_queryset(self, request: HttpRequest):
        owner_name = request.user.username
        qs = super().get_queryset(request)

        agent_branch = Agent.objects.filter(
            target=OuterRef("agent"),
            owner__name=owner_name,
        ).order_by("-timestamp")

        qs = qs.annotate(
            agent_branch_id=Subquery(agent_branch.values("id")[:1]),
            agent_branch_name=Subquery(agent_branch.values("name")[:1]),
        )

        return qs.filter(session__owner__name=owner_name).order_by("-timestamp")

    @admin.display(description="Session")
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
