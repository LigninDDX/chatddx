# src/chatddx_backend/agents/admin/forms/output_type.py
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
from chatddx_backend.agents.admin.schemas import OutputTypeFormData
from chatddx_backend.agents.models import CoercionChoices, ValidationChoices


class OutputTypeForm(ModelForm):
    class Meta:
        model = proxies.OutputType
        fields = []

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)
        if self.data:
            self.data = self.data.copy()
            self.data.pop("template", None)

    @classmethod
    def get_initial(cls, trail_model, name=None):
        return OutputTypeFormData.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump(mode="json")

    name = CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(
            attrs={"placeholder": "e.g., JSON User Profile Extractor"}
        ),
        label="Output Profile Name",
        help_text="Create a new output profile, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = ModelChoiceField(
        queryset=proxies.OutputType.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
        widget=UnfoldAdminSelect2Widget(),
        label="Output Template",
        help_text="Optional. Select a pre-configured template to populate the schema and strategies below.",
    )
    validation_strategy = ChoiceField(
        choices=ValidationChoices.choices,
        widget=UnfoldAdminSelect2Widget(),
        label="Error Handling Strategy",
        help_text="What happens if the output fails to match the schema (e.g., Retry generation, attach an Error message, Crash, or Ignore).",
    )
    coercion_strategy = ChoiceField(
        choices=CoercionChoices.choices,
        widget=UnfoldAdminSelect2Widget(),
        label="Enforcement Strategy",
        help_text="How the model is forced to follow the schema (e.g., via System Prompts, Native JSON decoding, or Tool/Function Calling).",
    )
    definition = CharField(
        required=False,
        widget=UnfoldAdminExpandableTextareaWidget(
            attrs={
                "placeholder": 'type = "object"\n\n[properties.summary]\ntype = "string"\n\n[properties.score]\ntype = "number"'
            }
        ),
        label="Schema Definition (TOML)",
        help_text="Define the required JSONSchema output structure using TOML formatting. Leave blank to accept unstructured plain text.",
    )

    helper = FormHelper()
    helper.form_tag = False
    helper.include_media = False

    helper.layout = Layout(
        Fieldset(
            "Output Structure",
            Row(
                Column(
                    "name",
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
                    Row("validation_strategy"),
                    Row("coercion_strategy"),
                    css_class="w-1/2",
                ),
                Column(
                    Row("definition"),
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        ),
    )
