# src/chatddx_backend/agents/admin/forms/agent.py

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django import forms
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx_backend.agents.admin import proxies


class AgentForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Agent name",
        help_text="Create a new agent, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = forms.ModelChoiceField(
        queryset=proxies.Connection.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
        widget=UnfoldAdminSelect2Widget(),
        label="Base Template",
        help_text="Optional. Select a pre-configured template to quickly populate the settings below.",
    )
    make_template = forms.BooleanField(
        required=False,
        initial=False,
        label="Save as Template",
        help_text="Make this exact configuration available as a reusable template for future agents.",
    )
    instructions = forms.CharField(
        required=False,
        widget=UnfoldAdminExpandableTextareaWidget(
            attrs={"placeholder": "No instructions provided"}
        ),
        label="System instructions",
        help_text="The core system prompt that dictates the agent's persona, rules, and boundaries.",
    )

    helper = FormHelper()

    helper.layout = Layout(
        Fieldset(
            "Agent Settings",
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
            Row(
                Column("instructions"),
                css_class="w-1/2",
            ),
            css_class="mb-8",
        )
    )
