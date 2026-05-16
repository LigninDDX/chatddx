from typing import Any

from django.forms import ModelForm
from pydantic import BaseModel


class BaseForm(ModelForm):
    class Meta:
        fields = ["name"]

    form_data: BaseModel

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        _ = kwargs.pop("request", None)
        _ = kwargs.pop("is_subform", None)

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)

        if self.data:
            self.data = self.data.copy()
            self.data.pop("template", None)

    @classmethod
    def get_initial(cls, trail_model, name=None):
        return cls.form_data.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump(
            mode="json",
            exclude_none=True,
        )
