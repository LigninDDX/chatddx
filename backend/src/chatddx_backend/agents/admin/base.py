# src/chatddx_backend/agents/admin/base.py
import json
from typing import Any, Generic, TypeVar, cast

from django.contrib import admin, messages
from django.db.models import Model as DjangoModel
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin

from chatddx_backend.agents.admin import proxies
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
from chatddx_backend.agents.models.loader import agent_relations
from chatddx_backend.agents.schemas import (
    AgentSchemaRef,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchemaRef,
    ToolSchema,
)
from chatddx_backend.agents.trail import TrailModel


def get_owned_trails(model, owner_name):
    BranchModel, FormData, TrailModel, _, _ = branch_map[model]

    indirectly_owned = Q(agentmodel__branches__owner__name=owner_name)
    directly_owned = Q(branches__owner__name=owner_name)

    if model in ("tool", "agent"):
        owned = directly_owned
    else:
        owned = directly_owned | indirectly_owned

    branches = _qs_canon(BranchModel.objects, owner_name)
    branchless_trails = (
        TrailModel.objects.filter(owned).filter(branches__isnull=True).distinct()
    )

    form_data = {}
    for branch in branches:
        form_data[str(branch.target.pk)] = FormData.model_validate(
            branch.target,
            context={"name": branch.name},
        )
    for trail in branchless_trails:
        form_data[str(trail.pk)] = FormData.model_validate(
            trail,
            context={"name": trail.fingerprint[:6]},
        )
    return form_data


def get_template_data(request):
    td = TemplateData(
        **{
            model: get_owned_trails(model, request.user.username)
            for model in branch_map
        }
    )
    return td.model_dump_json()


def _qs_canon(qs, owner_name):
    return (
        qs.filter(owner__name=owner_name)
        .order_by("owner_id", "name", "-timestamp")
        .distinct("owner_id", "name")
    )


def qs_super_agent(qs, owner_name):
    def subquery(owner_name, model, column):
        return (
            branch_map[model][0]
            .objects.filter(
                target=OuterRef(f"target__{model}"),
                owner__name=owner_name,
            )
            .values(column)[:1]
        )

    branch_annotations = {
        f"{model}_{field}": Subquery(subquery(owner_name, model, field))
        for field in ("name", "id")
        for model in agent_relations
    }
    return qs.select_related(
        *[f"target__{model}" for model in agent_relations]
    ).annotate(**branch_annotations)


def get_branch_model(model_name, owner_name, data):
    _, FormData, TrailModel, TrailSchema, Proxy = branch_map[model_name]

    form_data = FormData.model_validate(data)
    schema = TrailSchema.model_validate(form_data.model_dump(exclude_none=True))
    name = data.get("name", "")

    trail, _ = TrailModel.objects.get_or_create(
        fingerprint=schema.fingerprint,
        defaults=schema.model_dump(),
    )

    canon = _qs_canon(
        Proxy.objects.filter(name=name),
        owner_name,
    ).first()

    if canon and schema.fingerprint == canon.target.fingerprint:
        return canon

    return Proxy(
        target=trail,
        owner=IdentityModel.objects.get(name=owner_name),
        name=name,
    )


branch_map = {
    "agent": (
        AgentBranchModel,
        AgentFormData,
        AgentModel,
        AgentSchemaRef,
        proxies.Agent,
    ),
    "connection": (
        ConnectionBranchModel,
        ConnectionFormData,
        ConnectionModel,
        ConnectionSchema,
        proxies.Connection,
    ),
    "sampling_params": (
        SamplingParamsBranchModel,
        SamplingParamsFormData,
        SamplingParamsModel,
        SamplingParamsSchema,
        proxies.SamplingParams,
    ),
    "output_type": (
        OutputTypeBranchModel,
        OutputTypeFormData,
        OutputTypeModel,
        OutputTypeSchema,
        proxies.OutputType,
    ),
    "tool_group": (
        ToolGroupBranchModel,
        ToolGroupFormData,
        ToolGroupModel,
        ToolGroupSchemaRef,
        proxies.ToolGroup,
    ),
    "tool": (
        ToolBranchModel,
        ToolFormData,
        ToolModel,
        ToolSchema,
        proxies.Tool,
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
    add_form_template = "admin/agents/branch_change_form.html"
    list_display = [
        "name",
        "versions",
    ]

    @admin.display(description="Versions")
    def versions(self, obj):
        return self.model.objects.filter(name=obj.name).count()

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __new__(cls, *args, **fkwargs):
                fkwargs["request"] = request
                fkwargs["model_name"] = self.name
                return Form(*args, **fkwargs)

        return FormWithRequest

    def save_form(self, request, form, change):
        obj = form.actual_obj
        if obj.pk:
            self.message_user(
                request,
                "No changes detected. The current version is up to date.",
                level=messages.INFO,
            )
            request._skip_success_message = True
        else:
            obj.save()

        return obj

    def save_related(self, request, form, formsets, change):
        pass

    def response_change(self, request, obj):
        if "_continue" not in request.POST:
            return super().response_change(request, obj)

        opts = self.model._meta
        redirect_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(obj.pk,),
        )
        return HttpResponseRedirect(redirect_url)

    def response_add(self, request, obj, post_url_continue=None):
        if "_continue" not in request.POST:
            return super().response_add(request, obj, post_url_continue)

        opts = self.model._meta
        redirect_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(obj.pk,),
        )
        return HttpResponseRedirect(redirect_url)

    def get_form_context(self, request: HttpRequest, obj: Any) -> dict[str, Any]:
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
        return _qs_canon(qs, request.user.username)

    def delete_queryset(self, request, queryset):
        names_subquery = queryset.values_list("name", flat=True)
        self.model.objects.filter(name__in=names_subquery).delete()

    def render_change_form(
        self,
        request,
        context,
        add=False,
        change=False,
        form_url="",
        obj=None,
    ):
        context = {**context, **self.get_form_context(request, obj)}
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
