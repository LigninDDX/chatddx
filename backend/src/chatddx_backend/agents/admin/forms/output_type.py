# src/chatddx_backend/agents/admin/forms/output_type.py
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    Form,
    ModelChoiceField,
)
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.models import CoercionChoices, ValidationChoices


class OutputTypeForm(Form):
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
    make_template = BooleanField(
        required=False,
        initial=False,
        label="Save as Template",
        help_text="Make this output configuration available as a reusable template.",
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
    definition_toml = CharField(
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

    helper.layout = Layout(
        Fieldset(
            "Output Structure",
            Row(
                Column(
                    Row("name"),
                    Row("make_template"),
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
                    "definition_toml",
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        ),
    )
