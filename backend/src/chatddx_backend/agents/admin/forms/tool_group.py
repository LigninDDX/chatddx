# src/chatddx_backend/agents/admin/forms/tool_group.py
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django.forms import (
    BooleanField,
    CharField,
    Form,
    ModelChoiceField,
)
from unfold.fields import ModelMultipleChoiceField
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx_backend.agents.admin import proxies


class ToolGroupForm(Form):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.fields["tools"].queryset = proxies.Tool.objects.all()

    name = CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(
            attrs={"placeholder": "e.g., Web Search & Math Suite"}
        ),
        label="Tool Group Name",
        help_text="Create a new tool group, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = ModelChoiceField(
        queryset=proxies.ToolGroup.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
        widget=UnfoldAdminSelect2Widget(),
        label="Tool Group Template",
        help_text="Optional. Select a pre-configured template to populate the tools and instructions below.",
    )
    make_template = BooleanField(
        required=False,
        initial=False,
        label="Save as Template",
        help_text="Make this exact combination of tools and instructions available as a reusable template.",
    )
    tools = ModelMultipleChoiceField(
        queryset=proxies.Tool.objects.none(),
        widget=UnfoldAdminSelect2Widget(attrs={"multiple": "multiple"}),
        required=False,
        label="Available Tools",
        help_text="Select the specific functions, APIs, or integrations this agent is permitted to execute.",
    )
    instructions = CharField(
        required=False,
        widget=UnfoldAdminExpandableTextareaWidget(
            attrs={
                "placeholder": "e.g., Always use the web search tool before answering factual questions. Do not use the calculator for simple arithmetic."
            }
        ),
        label="Tool Usage Instructions",
        help_text="Specific guidelines dictating exactly when and how the agent should utilize the selected tools. This is appended to the main system prompt.",
    )

    helper = FormHelper()

    helper.layout = Layout(
        Fieldset(
            "Tool Group Settings",
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
                    "tools",
                    css_class="w-1/2",
                ),
                Column(
                    "instructions",
                    css_class="w-1/2",
                ),
            ),
        ),
    )
