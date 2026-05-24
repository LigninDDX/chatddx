# src/chatddx/django/portal/admin/forms/agent.py
from typing import Any, final

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django import forms
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx.django.portal.forms.base import BaseForm
from chatddx.repo import proxies
from chatddx.repo.form_data_in import AgentFormDataIn
from chatddx.repo.form_data_out import AgentFormDataOut
from chatddx.repo.shufflers.main import qs_canon, qs_owned_trails
from chatddx.repo.trail_models import (
    ConnectionTrailModel,
    OutputTypeTrailModel,
    SamplingParamsTrailModel,
    ToolGroupTrailModel,
)


@final
class AgentForm(BaseForm):
    form_data_in = AgentFormDataIn
    form_data_out = AgentFormDataOut

    @final
    class Meta(BaseForm.Meta):
        model = proxies.Agent

    def __init__(self, *args: Any, **kwargs: Any):
        request = kwargs["request"]

        super().__init__(*args, **kwargs)

        owner = request.user.username
        owned = qs_canon(proxies.Agent.objects.all(), owner)

        self.fields["template"].choices = [(model.pk, model.name) for model in owned]

        self.fields["connection"].queryset = qs_owned_trails(  # pyright: ignore[reportAttributeAccessIssue]
            ConnectionTrailModel.objects.all(), owner
        )
        self.fields["sampling_params"].queryset = qs_owned_trails(  # pyright: ignore[reportAttributeAccessIssue]
            SamplingParamsTrailModel.objects.all(), owner
        )
        self.fields["output_type"].queryset = qs_owned_trails(  # pyright: ignore[reportAttributeAccessIssue]
            OutputTypeTrailModel.objects.all(), owner
        )
        self.fields["tool_group"].queryset = qs_owned_trails(  # pyright: ignore[reportAttributeAccessIssue]
            ToolGroupTrailModel.objects.all(), owner
        )

    def clean_tool_group(self):
        tool_group = self.cleaned_data["tool_group"]
        tool_group.tools = proxies.Tool.objects.filter(pk__in=tool_group.tools)
        return tool_group

    name = forms.CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Agent name",
        help_text="Create a new agent, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = forms.ChoiceField(
        required=False,
        widget=UnfoldAdminSelect2Widget(),
        label="Base Template",
        help_text="Optional. Select a pre-configured template to quickly populate the settings below.",
    )
    instructions = forms.CharField(
        required=False,
        widget=UnfoldAdminExpandableTextareaWidget(
            attrs={"placeholder": "No instructions provided"}
        ),
        label="System instructions",
        help_text="The core system prompt that dictates the agent's persona, rules, and boundaries.",
    )
    connection = forms.ModelChoiceField(
        queryset=ConnectionTrailModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Connection",
    )
    sampling_params = forms.ModelChoiceField(
        queryset=SamplingParamsTrailModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Sampling Parameters",
    )
    output_type = forms.ModelChoiceField(
        queryset=OutputTypeTrailModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Output Type",
    )
    tool_group = forms.ModelChoiceField(
        queryset=ToolGroupTrailModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Tool Group",
    )

    @property
    def helper(self):
        helper = FormHelper()
        helper.form_tag = False
        helper.include_media = False

        main_section = Fieldset(
            "Agent Settings",
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
            Row(
                Column("instructions"),
                css_class="w-1/2",
            ),
            css_class="mb-8",
        )
        relations_section = Fieldset(
            "Agent Relations",
            Row(
                Column(
                    "connection",
                    "sampling_params",
                    css_class="w-1/2",
                ),
                Column(
                    "output_type",
                    "tool_group",
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        )

        helper.layout = Layout(main_section, relations_section)

        return helper
