# src/chatddx/django/portal/forms/base.py
from typing import Any, override

from django.forms import ModelForm
from pydantic import ValidationError as PydanticValidationError

from chatddx.repo.base import BaseFormDataIn, BaseFormDataOut, BranchModel
from chatddx.repo.shufflers.main import (
    load_form_data,
    qs_canon,
)


class BaseForm(ModelForm):
    class Meta:
        fields = ["name"]

    form_data_out: type[BaseFormDataOut]
    form_data_in: type[BaseFormDataIn]

    validated_data: BaseFormDataIn | None

    def validate(self, data: dict[str, Any]):
        try:
            validated_data = self.form_data_in.model_validate(data)
            return validated_data
        except PydanticValidationError as e:
            for error in e.errors():
                self.add_error(str(error["loc"][0]), error["msg"])

    @override
    def clean(self):
        cleaned = super().clean()
        self.validated_data = self.validate(cleaned)
        return cleaned

    def get_initial(self, instance: BranchModel):
        return load_form_data(instance).model_dump(by_alias=True)

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        self.request = kwargs.pop("request")
        self.validated_data = None

        if instance:
            kwargs["initial"] = self.get_initial(instance)

        super().__init__(*args, **kwargs)
        owner = self.request.user.username
        owned = qs_canon(self._meta.model.objects.all(), owner)

        self.fields["template"].choices = [("", "=== clear ===")] + [
            (model.target.pk, model.name) for model in owned
        ]

        if self.data:
            self.data = self.data.copy()
            self.data.pop("template", None)
