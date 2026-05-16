# src/chatddx_backend/agents/admin/forms/tool_group.py
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django.forms import (
    CharField,
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
from chatddx_backend.agents.admin.forms.base import BaseForm
from chatddx_backend.agents.admin.schemas import ToolGroupFormData
from chatddx_backend.agents.models import ToolModel


class ToolGroupForm(BaseForm):
    form_data = ToolGroupFormData

    class Meta(BaseForm.Meta):
        model = proxies.ToolGroup

    def __init__(self, *args, **kwargs):
        request = kwargs["request"]
        super().__init__(*args, **kwargs)

        self.fields["tools"].queryset = ToolModel.objects.filter(
            branches__owner__name=request.user.username
        ).distinct()

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
    tools = ModelMultipleChoiceField(
        queryset=ToolModel.objects.none(),
        # widget=UnfoldAdminSelect2Widget(attrs={"multiple": "multiple"}),
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
    helper.include_media = False
    helper.form_tag = False

    helper.layout = Layout(
        Fieldset(
            "Tool Group Settings",
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
