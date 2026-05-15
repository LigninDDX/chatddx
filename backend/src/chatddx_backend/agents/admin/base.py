# src/chatddx_backend/agents/admin/base.py
import json
from typing import Any, Generic, TypeVar, cast

from django.contrib import messages
from django.db.models import Model as DjangoModel
from django.db.models import OuterRef, QuerySet, Subquery
from django.http import HttpRequest
from unfold.admin import ModelAdmin

from chatddx_backend.agents.admin.schemas import (
    AgentFormData,
    ConnectionFormData,
    OutputTypeFormData,
    SamplingParamsFormData,
    TemplateData,
    ToolFormData,
    ToolGroupFormData,
)
from chatddx_backend.agents.models import (
    AgentModel,
    ConnectionModel,
    IdentityModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
    ToolModel,
)
from chatddx_backend.agents.models.history import (
    AgentBranchModel,
    BranchModel,
    ConnectionBranchModel,
    OutputTypeBranchModel,
    SamplingParamsBranchModel,
    ToolBranchModel,
    ToolGroupBranchModel,
)
from chatddx_backend.agents.schemas import (
    AgentSchema,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolSchema,
)
from chatddx_backend.agents.trail import TrailModel


def _get_branches(model, request):
    BranchModel, FormData, TrailModel, _ = branch_map[model]
    branches = {
        str(instance.target.pk): FormData.model_validate(
            instance.target,
            context={"name": instance.name},
        )
        for instance in _qs_canon(BranchModel.objects, request)
    }
    if model == "agent":
        return branches

    if model == "tool":
        return branches

    qs = (
        qs_agent_list(AgentBranchModel.objects, request)
        .filter(**{f"{model}_id__isnull": True})
        .values_list(f"target__{model}_id", flat=True)
        .distinct()
    )

    for branchless_trail in TrailModel.objects.filter(id__in=qs):
        label = branchless_trail.fingerprint[:6]

        branches[str(branchless_trail.pk)] = FormData.model_validate(
            branchless_trail,
            context={"name": label},
        )
    return branches


def get_template_data(request):
    td = TemplateData(**{model: _get_branches(model, request) for model in branch_map})
    return td.model_dump_json()


def _qs_owned(qs, request):
    return qs.filter(owner__name=request.user.username)


def _qs_canon(qs, request):
    return (
        _qs_owned(qs, request)
        .order_by("owner_id", "name", "-timestamp")
        .distinct("owner_id", "name")
    )


def qs_agent_list(qs, request):
    agent_relations = ["connection", "sampling_params", "output_type", "tool_group"]
    branch_annotations = {
        f"{model}_{field}": Subquery(_branch_subquery(request, model, field))
        for field in ("name", "id")
        for model in agent_relations
    }
    return (
        _qs_owned(qs, request)
        .select_related(*[f"target__{model}" for model in agent_relations])
        .annotate(**branch_annotations)
    )


def _branch_subquery(request, model, column):
    return (
        branch_map[model][0]
        .objects.filter(
            target=OuterRef(f"target__{model}"),
            owner__name=request.user.username,
        )
        .values(column)[:1]
    )


branch_map = {
    "agent": (
        AgentBranchModel,
        AgentFormData,
        AgentModel,
        AgentSchema,
    ),
    "connection": (
        ConnectionBranchModel,
        ConnectionFormData,
        ConnectionModel,
        ConnectionSchema,
    ),
    "sampling_params": (
        SamplingParamsBranchModel,
        SamplingParamsFormData,
        SamplingParamsModel,
        SamplingParamsSchema,
    ),
    "output_type": (
        OutputTypeBranchModel,
        OutputTypeFormData,
        OutputTypeModel,
        OutputTypeSchema,
    ),
    "tool_group": (
        ToolGroupBranchModel,
        ToolGroupFormData,
        ToolGroupModel,
        ToolGroupSchema,
    ),
    "tool": (
        ToolBranchModel,
        ToolFormData,
        ToolModel,
        ToolSchema,
    ),
}


T = TypeVar("T", bound="DjangoModel")


class TypedModelAdmin(ModelAdmin, Generic[T]):
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        return cast(QuerySet[T], super().get_queryset(request))


S = TypeVar("S", bound="TrailModel")


class TrailModelAdmin(TypedModelAdmin[S]):
    def get_queryset(self, request: HttpRequest) -> QuerySet[S]:
        qs: QuerySet[S] = super().get_queryset(request)
        return qs


B = TypeVar("B", bound="BranchModel")


class BranchModelAdmin(TypedModelAdmin[S]):
    name: str
    change_form_template = "admin/agents/branch_change_form.html"

    def get_change_form_context(self, request: HttpRequest, obj: Any) -> dict[str, Any]:
        return {
            "template_data": get_template_data(request),
            "form_info": json.dumps(
                {
                    "name": self.name,
                    self.name: obj.target.pk if obj else None,
                }
            ),
        }

    def get_queryset(self, request):
        qs: QuerySet[S] = super().get_queryset(request)
        return _qs_canon(qs, request)

    def save_model(self, request, obj, form, change):
        owner, _ = IdentityModel.objects.get_or_create(name=request.user.username)
        form_data = branch_map[self.name][1].model_validate(form.cleaned_data)
        schema = branch_map[self.name][3].model_validate(
            form_data.model_dump(exclude_none=True)
        )
        name = form.cleaned_data["name"]

        trail, _ = branch_map[self.name][2].objects.get_or_create(
            fingerprint=schema.fingerprint,
            defaults=schema.model_dump(),
        )

        canon = _qs_canon(
            branch_map[self.name][0].objects.filter(name=name),
            request,
        ).first()

        if canon and schema.fingerprint == canon.target.fingerprint:
            self.message_user(
                request,
                f"No changes detected. The current version (saved {canon.timestamp.strftime('%Y-%m-%d %H:%M')}) is up to date.",
                level=messages.INFO,
            )

            request._skip_success_message = True
            return

        obj.target = trail
        obj.owner = owner
        obj.name = name
        super().save_model(request, obj, form, change)

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        context = {**context, **self.get_change_form_context(request, obj)}
        if obj and hasattr(obj, "name"):
            timeline = list(
                self.model.objects.filter(
                    owner__name=request.user.username,
                    name=obj.name,
                )
                .order_by("timestamp")
                .values_list("pk", "timestamp")
            )

            pks = [item[0] for item in timeline]
            try:
                idx = pks.index(obj.pk)

                if idx > 0:
                    prev_pk, prev_ts = timeline[idx - 1]
                    context["prev_"] = {
                        "pk": prev_pk,
                        "text": f"Older ({prev_ts.strftime('%Y-%m-%d %H:%M')})",
                    }

                if idx < len(pks) - 1:
                    next_pk, next_ts = timeline[idx + 1]
                    context["next_"] = {
                        "pk": next_pk,
                        "text": f"Newer ({next_ts.strftime('%Y-%m-%d %H:%M')})",
                    }

                context["version_info"] = {"current": idx + 1, "total": len(pks)}
            except ValueError:
                pass

        return super().render_change_form(request, context, add, change, form_url, obj)

    def message_user(self, request, message, level=messages.SUCCESS, **kwargs):
        if (
            getattr(request, "_skip_success_message", False)
            and level == messages.SUCCESS
        ):
            return
        return super().message_user(request, message, level=level, **kwargs)
