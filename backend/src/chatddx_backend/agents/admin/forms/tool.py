# src/chatddx_backend/agents/admin/forms/tool.py
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django.forms import (
    CharField,
    ChoiceField,
    ModelChoiceField,
    ModelForm,
)
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.admin.schemas import ToolFormData
from chatddx_backend.agents.models import ToolChoices


class ToolForm(ModelForm):
    class Meta:
        model = proxies.Tool
        fields = []

    def __init__(self, *args: Any, **kwargs: Any):
        self.request = kwargs.pop("request", None)
        instance = kwargs.get("instance")

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)

        if self.data:
            self.data = self.data.copy()
            del self.data["template"]

    @classmethod
    def get_initial(cls, trail_model, name=None):
        return ToolFormData.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump()

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    name = CharField(
        max_length=255,
        required=False,
        widget=UnfoldAdminTextInputWidget(),
        label="Tool Name",
        help_text="Create a new tool, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = ModelChoiceField(
        queryset=proxies.Tool.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
        widget=UnfoldAdminSelect2Widget(),
        label="Tool Template",
        help_text="Optional. Select a pre-configured template to populate the tools and instructions below.",
    )
    command = CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Command",
        help_text="The exact model identifier required by your chosen provider.",
    )
    type = ChoiceField(
        choices=ToolChoices.choices,
        widget=UnfoldAdminSelect2Widget(),
        label="Tool Type",
        help_text="The service hosting the selected model.",
    )
    parameters_toml = CharField(
        required=False,
        widget=UnfoldAdminExpandableTextareaWidget(),
        label="Parameter Definition (TOML)",
        help_text="Define the required JSONSchema output structure using TOML formatting.",
    )

    helper = FormHelper()
    helper.include_media = False
    helper.form_tag = False

    helper.layout = Layout(
        Fieldset(
            "Tool Settings",
            Row(
                Column(
                    Row("name"),
                    css_class="w-1/2",
                ),
                Column(
                    "template",
                    css_class="w-1/2",
                ),
            ),
            Hr(),
            Row(
                Column(
                    Row("command"),
                    Row("type"),
                    css_class="w-1/2",
                ),
                Column(
                    "parameters_toml",
                    css_class="w-1/2",
                ),
            ),
        ),
    )
