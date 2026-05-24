# src/chatddx/django/portal/forms/base.py
from typing import Any

from django.forms import ModelForm
from pydantic import ValidationError as PydanticValidationError

from chatddx.repo.base import BaseFormDataIn, BaseFormDataOut, TrailModel
from chatddx.repo.shufflers.main import qs_canon


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

    def clean(self):
        cleaned = super().clean()
        self.validated_data = self.validate(cleaned)
        return cleaned

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        request = kwargs.pop("request")
        self.validated_data = None

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)
        owner = request.user.username
        owned = qs_canon(self._meta.model.objects.all(), owner)

        self.fields["template"].choices = [(model.pk, model.name) for model in owned]

        if self.data:
            self.data = self.data.copy()
            self.data.pop("template", None)

    @classmethod
    def get_initial(cls, trail_model: TrailModel, name: str | None = None):
        return cls.form_data_out.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump(by_alias=True)
