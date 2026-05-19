# src/chatddx/django/repo/admin/base.py
import json
from typing import Any, TypeVar, cast, get_args, no_type_check

from django.contrib import admin, messages
from django.db.models import Model as DjangoModel
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from pydantic import BaseModel
from unfold.admin import ModelAdmin

from chatddx.django.portal.forms.base import BaseForm
from chatddx.repo.base import BaseFormData, BranchModel, TrailModel
from chatddx.repo.form_data import (
    AgentFormData,
    ConnectionFormData,
    OutputTypeFormData,
    SamplingParamsFormData,
    ToolFormData,
    ToolGroupFormData,
)
from chatddx.repo.loaders.model_loader import agent_relations
from chatddx.repo.main import BundleName, Repo


class TemplateData(BaseModel):
    agent: dict[str, AgentFormData]
    connection: dict[str, ConnectionFormData]
    sampling_params: dict[str, SamplingParamsFormData]
    output_type: dict[str, OutputTypeFormData]
    tool_group: dict[str, ToolGroupFormData]
    tool: dict[str, ToolFormData]


def get_owned_trails(model: str, owner_name: str) -> dict[str, BaseFormData]:
    BM = Repo(model, BranchModel)
    FD = Repo(model, BaseFormData)
    TM = Repo(model, TrailModel)

    indirectly_owned = Q(agenttrailmodel__branches__owner__name=owner_name)
    directly_owned = Q(branches__owner__name=owner_name)

    if model in ("tool", "agent"):
        owned = directly_owned
    else:
        owned = directly_owned | indirectly_owned

    branches = qs_canon(BM.objects.all(), owner_name)  # pyright: ignore[reportArgumentType]
    branchless_trails = (
        TM.objects.filter(owned).filter(branches__isnull=True).distinct()
    )

    form_data: dict[str, BaseFormData] = {}
    for branch in branches:
        form_data[str(branch.target.pk)] = FD.model_validate(
            branch.target,
            context={"name": branch.name},
        )
    for trail in branchless_trails:
        form_data[str(trail.pk)] = FD.model_validate(
            trail,
            context={"name": trail.fingerprint[:6]},
        )
    return form_data


def get_template_data(owner_name: str):
    payload: dict[str, Any] = {
        model: get_owned_trails(model, owner_name) for model in get_args(BundleName)
    }
    td = TemplateData(**payload)
    return td.model_dump_json()


DjangoModelT = TypeVar("DjangoModelT", bound=DjangoModel)


def qs_canon(qs: QuerySet[DjangoModelT], owner_name: str) -> QuerySet[DjangoModelT]:
    return (
        qs.filter(owner__name=owner_name)
        .order_by("owner_id", "name", "-timestamp")
        .distinct("owner_id", "name")
    )


def qs_super_agent(qs: QuerySet[DjangoModelT], owner_name: str):
    def subquery(owner_name: str, model: str, column: str):
        BM = Repo(model, BranchModel)

        return BM.objects.filter(
            target=OuterRef(f"target__{model}"),
            owner__name=owner_name,
        ).values(column)[:1]

    branch_annotations = {
        f"{model}_{field}": Subquery(subquery(owner_name, model, field))
        for field in ("name", "id")
        for model in agent_relations
    }
    return qs.select_related(
        *[f"target__{model}" for model in agent_relations]
    ).annotate(**branch_annotations)


class TypedModelAdmin[T: DjangoModel](ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        return cast(QuerySet[T], super().get_queryset(request))


class TrailModelAdmin[T: TrailModel](TypedModelAdmin[T]):
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        qs: QuerySet[T] = super().get_queryset(request)
        return qs


class BranchModelAdmin[T: BranchModel](TypedModelAdmin[T]):
    name: str
    change_form_template = "admin/agents/branch_change_form.html"
    add_form_template = "admin/agents/branch_change_form.html"
    list_display = [
        "name",
        "versions",
    ]

    @admin.display(description="Versions")
    def versions(self, obj: DjangoModel) -> int:
        return self.model.objects.filter(name=obj.name).count()  # pyright: ignore

    def get_form(
        self,
        request: HttpRequest,
        obj: DjangoModel | None = None,
        change: bool = False,
        **kwargs: Any,
    ):
        Form = super().get_form(request, obj, **kwargs)  # pyright: ignore

        class FormWithRequest(Form):
            def __new__(cls, *args: Any, **fkwargs: Any):
                fkwargs["request"] = request
                fkwargs["model_name"] = self.name
                return Form(*args, **fkwargs)

        return FormWithRequest

    def save_form(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        request: HttpRequest,
        form: BaseForm,
        change: bool,
    ):
        obj = form.actual_obj
        if obj.pk:
            self.message_user(  # pyright: ignore[reportUnknownMemberType]
                request,
                "No changes detected. The current version is up to date.",
                level=messages.INFO,
            )
            request._skip_success_message = True  # pyright: ignore[reportAttributeAccessIssue]
        else:
            obj.save()

        return obj

    def save_related(self, request, form, formsets, change):  # pyright: ignore[reportMissingParameterType]
        pass

    @no_type_check
    def response_change(self, request: HttpRequest, obj: DjangoModel):
        if "_continue" not in request.POST:
            return super().response_change(request, obj)

        opts = self.model._meta
        redirect_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(obj.pk,),
        )
        return HttpResponseRedirect(redirect_url)

    @no_type_check
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
            "template_data": get_template_data(request.user.username),
            "form_info": json.dumps(
                {
                    "name": self.name,
                    self.name: obj.target.pk if obj else None,
                }
            ),
        }

    def get_queryset(self, request: HttpRequest):
        qs: QuerySet[Any] = super().get_queryset(request)
        return qs_canon(qs, request.user.username)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[DjangoModel]):
        names_subquery = queryset.values_list("name", flat=True)
        self.model.objects.filter(name__in=names_subquery).delete()  # pyright: ignore[reportUnknownMemberType]

    @no_type_check
    def render_change_form(
        self,
        request: HttpRequest,
        context: dict[str, Any],
        add: bool = False,
        change: bool = False,
        form_url: str = "",
        obj: DjangoModel | None = None,
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

    @no_type_check
    def message_user(self, request, message, level=messages.SUCCESS, **kwargs):
        if (
            getattr(request, "_skip_success_message", False)
            and level == messages.SUCCESS
        ):
            return
        return super().message_user(request, message, level=level, **kwargs)
