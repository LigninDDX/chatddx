# src/chatddx_backend/agents/admin/history.py
import json
from dataclasses import asdict
from typing import Any

from django.contrib import admin
from django.db.models import Max, Min, QuerySet
from django.forms import ValidationError
from django.http import HttpRequest
from django.urls import reverse
from django.utils.formats import date_format
from markdown import markdown
from unfold.admin import mark_safe
from unfold.utils import format_html

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.admin.base import (
    BranchModelAdmin,
    TypedModelAdmin,
    _qs_canon,
    get_template_data,
    qs_agent_list,
)
from chatddx_backend.agents.admin.forms import (
    ConnectionForm,
    OutputTypeForm,
    SamplingParamsForm,
    ToolGroupForm,
    agent_plus,
)
from chatddx_backend.agents.admin.forms.tool import ToolForm
from chatddx_backend.agents.admin.utils import (
    get_step_nav,
    truncate_content,
)


def _get_branch_link(obj, field_name):
    branch_id = getattr(obj, f"{field_name}_id")
    branch_name = getattr(obj, f"{field_name}_name")
    target = getattr(obj.target, field_name)
    label = branch_name or target.fingerprint[:6]
    if branch_id:
        url = (
            reverse(
                f"admin:agents_{field_name.replace('_', '')}_change",
                args=[branch_id],
            )
            + f"?from_agent={obj.pk}"
        )
    else:
        url = (
            reverse(
                f"admin:agents_{field_name.replace('_', '')}_add",
            )
            + f"?from_agent={obj.pk}&target={target.id}"
        )

    return format_html('<a href="{}">{}</a>', url, label)


@admin.register(proxies.Agent)
class AgentAdmin(BranchModelAdmin[proxies.Agent]):
    form = agent_plus.AgentPlusForm
    name = "agent"

    list_display = [
        "__str__",
        "instructions",
        "connection",
        "output_type",
        "sampling_params",
        "tool_group",
    ]

    @admin.display(description="Instructions", ordering="target__instructions")
    def instructions(self, obj):
        return obj.target.instructions[:20]

    @admin.display(description="Connection", ordering="connection_name")
    def connection(self, obj):
        return _get_branch_link(obj, "connection")

    @admin.display(description="Output Type", ordering="output_type_name")
    def output_type(self, obj):
        return _get_branch_link(obj, "output_type")

    @admin.display(description="Sampling Params", ordering="sampling_params_name")
    def sampling_params(self, obj):
        return _get_branch_link(obj, "sampling_params")

    @admin.display(description="Tool Group", ordering="tool_group_name")
    def tool_group(self, obj):
        return _get_branch_link(obj, "tool_group")

    def get_change_form_context(
        self,
        request: HttpRequest,
        obj: Any,
    ) -> dict[str, Any]:
        agent_relations = ["connection", "sampling_params", "output_type", "tool_group"]
        form_info = {
            "name": "agent_plus",
            "agent": obj.target.pk,
        } | {model: getattr(obj.target, model).pk for model in agent_relations}

        return {
            "template_data": get_template_data(request),
            "form_info": json.dumps(form_info),
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs_agent_list(qs, request)

    def get_object(self, request, object_id, from_field=None):
        queryset = self.get_queryset(request)
        field = (
            self.model._meta.pk
            if from_field is None
            else self.model._meta.get_field(from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.attname: object_id})
        except (self.model.DoesNotExist, ValidationError, ValueError):
            return None


@admin.register(proxies.Connection)
class ConnectionAdmin(BranchModelAdmin[proxies.Connection]):
    form = ConnectionForm
    name = "connection"

    list_display = [
        "name",
        "_model",
        "provider",
        "endpoint",
    ]

    @admin.display(description="Model", ordering="target__model")
    def _model(self, obj):
        return obj.target.model

    @admin.display(description="Endpoint", ordering="target__endpoint")
    def endpoint(self, obj):
        return obj.target.endpoint

    @admin.display(description="Provider", ordering="target__provider")
    def provider(self, obj):
        return obj.target.get_provider_display()


@admin.register(proxies.SamplingParams)
class SamplingParamsAdmin(BranchModelAdmin[proxies.SamplingParams]):
    form = SamplingParamsForm
    name = "sampling_params"

    list_display = [
        "name",
        "seed",
        "temperature",
        "top_p",
    ]

    @admin.display(description="Seed", ordering="target__seed")
    def seed(self, obj):
        return obj.target.seed

    @admin.display(description="Temp", ordering="target__temperature")
    def temperature(self, obj):
        return obj.target.temperature

    @admin.display(description="Top-p", ordering="target__top_p")
    def top_p(self, obj):
        return obj.target.top_p


@admin.register(proxies.OutputType)
class OutputTypeAdmin(BranchModelAdmin[proxies.OutputType]):
    form = OutputTypeForm
    name = "output_type"

    list_display = [
        "name",
        "_type",
        "validation_strategy",
        "coercion_strategy",
    ]

    @admin.display(
        description="Coercion Strategy",
        ordering="target__coercion_strategy",
    )
    def coercion_strategy(self, obj):
        return obj.target.get_coercion_strategy_display()

    @admin.display(
        description="Type",
        ordering="target__definition",
    )
    def _type(self, obj):
        return obj.target.definition.get("type", None)

    @admin.display(
        description="Validation Strategy",
        ordering="target__validation_strategy",
    )
    def validation_strategy(self, obj):
        return obj.target.get_validation_strategy_display()


@admin.register(proxies.ToolGroup)
class ToolGroupAdmin(BranchModelAdmin[proxies.ToolGroup]):
    form = ToolGroupForm
    name = "tool_group"
    list_display = [
        "name",
    ]

    @admin.display(
        description="Coercion Strategy",
        ordering="target__coercion_strategy",
    )
    def coercion_strategy(self, obj):
        return obj.target.get_coercion_strategy_display()


@admin.register(proxies.Tool)
class ToolAdmin(BranchModelAdmin[proxies.Tool]):
    form = ToolForm
    name = "tool"

    list_display = [
        "name",
        "type",
    ]

    @admin.display(
        description="Type",
        ordering="target__type",
    )
    def type(self, obj):
        return obj.target.get_type_display()


@admin.register(proxies.Identity)
class IdentityAdmin(TypedModelAdmin[proxies.Identity]):
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
