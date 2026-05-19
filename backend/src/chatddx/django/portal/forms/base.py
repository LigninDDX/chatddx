# src/chatddx/django/repo/admin/forms/base.py
from typing import Any

from django.db.models import Model as DjangoModel
from django.forms import ModelForm
from django.http import HttpRequest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from chatddx.repo import proxies
from chatddx.repo.loaders.branches import get_branch_model
from chatddx.repo.main import is_bundle_name


class BaseForm(ModelForm):
    class Meta:
        fields = ["name"]

    form_data: type[BaseModel]
    model_name: str
    request: HttpRequest
    actual_obj: proxies.BranchProxy

    def clean(self):
        if not is_bundle_name(self.model_name):
            raise ValueError(f"Not a valid bundle '{self.model_name}'")
        try:
            self.actual_obj = get_branch_model(
                self.model_name,
                self.request.user.username,
                self.cleaned_data,
            )
        except PydanticValidationError as e:
            for error in e.errors():
                self.add_error(str(error["loc"][0]), error["msg"])

        return self.cleaned_data

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        self.request = kwargs.pop("request", None)
        self.model_name = kwargs.pop("model_name", None)
        _ = kwargs.pop("is_subform", None)

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)

        if self.data:
            self.data = self.data.copy()
            self.data.pop("template", None)

    @classmethod
    def get_initial(cls, trail_model: DjangoModel, name: str | None = None):
        return cls.form_data.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump(
            mode="json",
            exclude_none=True,
        )
