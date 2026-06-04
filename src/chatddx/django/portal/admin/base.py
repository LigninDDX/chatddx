# src/chatddx/django/repo/admin/base.py
import json
from typing import Any, cast, no_type_check, override

from django.contrib import admin, messages
from django.db.models import Model as DjangoModel
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin

from chatddx.django.portal.forms.base import BaseForm
from chatddx.repo.base import BranchModel, BranchProxy, TrailModel, TrailSchema
from chatddx.repo.main import BundleName, Repo
from chatddx.repo.shufflers.main import (
    dump_branch,
    load_template_data,
    qs_canon,
)


class TypedModelAdmin[T: DjangoModel](ModelAdmin):
    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        return cast(QuerySet[T], super().get_queryset(request))


class TrailModelAdmin[T: TrailModel](TypedModelAdmin[T]):
    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        qs: QuerySet[T] = super().get_queryset(request)
        return qs


class BranchModelAdmin[T: BranchModel](TypedModelAdmin[T]):
    name: BundleName
    change_form_template = "admin/agents/branch_change_form.html"
    add_form_template = "admin/agents/branch_change_form.html"
    list_display = [
        "name",
        "versions",
    ]

    @admin.display(description="Versions")
    def versions(self, obj: DjangoModel) -> int:
        return self.model.objects.filter(name=obj.name).count()

    def get_form(
        self,
        request: HttpRequest,
        obj: DjangoModel | None = None,
        change: bool = False,
        **kwargs: Any,
    ):
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __new__(cls, *args: Any, **fkwargs: Any):
                fkwargs["request"] = request
                return Form(*args, **fkwargs)

        return FormWithRequest

    @override
    def save_form(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        request: HttpRequest,
        form: BaseForm,
        change: bool,
    ) -> BranchProxy:
        if form.validated_data is None:
            raise ValueError("form.validated_data is unexpectedly None")

        schema_cls = Repo(self.name, TrailSchema)
        proxy_cls = Repo(self.name, BranchProxy)
        schema = schema_cls.model_validate(form.validated_data.model_dump())

        obj, created = dump_branch(
            self.name,
            form.validated_data.name or "",
            request.user.username,
            schema,
        )

        if not created:
            self.message_user(  # pyright: ignore[reportUnknownMemberType]
                request,
                "No changes detected. The current version is up to date.",
                level=messages.INFO,
            )
            request._skip_success_message = True  # pyright: ignore[reportAttributeAccessIssue]

        form.save()

        return obj.as_proxy(proxy_cls)

    @override
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
        owner = request.user.username
        return {
            "template_data": load_template_data(owner).model_dump_json(by_alias=True),
            "form_info": json.dumps(
                {
                    "template_selectors": [
                        {
                            "key": self.name,
                            "target": "#id_template",
                            "field_prefix": "",
                        }
                    ]
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
