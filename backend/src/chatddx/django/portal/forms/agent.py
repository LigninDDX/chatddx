# src/chatddx/django/[app-name]/admin/forms/agent.py
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django import forms
from django.db.models import OuterRef, Q, Subquery
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx.django.portal.forms.base import BaseForm
from chatddx.repo import proxies
from chatddx.repo.base import TrailModel
from chatddx.repo.form_data_in import AgentFormDataIn
from chatddx.repo.form_data_out import AgentFormDataOut
from chatddx.repo.loaders.model_loader import agent_relations
from chatddx.repo.main import Repo
from chatddx.repo.trail_models import (
    ConnectionTrailModel,
    OutputTypeTrailModel,
    SamplingParamsTrailModel,
    ToolGroupTrailModel,
)


class AgentForm(BaseForm):
    form_data_in = AgentFormDataIn
    form_data_out = AgentFormDataOut

    class Meta(BaseForm.Meta):
        model = proxies.Agent

    def __init__(self, *args: Any, **kwargs: Any):
        request = kwargs["request"]
        super().__init__(*args, **kwargs)

        for field_name in agent_relations:
            TM = Repo(field_name, TrailModel)
            branch_subquery = TM.objects.filter(pk=OuterRef("pk")).values(
                "branches__name"
            )[:1]

            self.fields[field_name].queryset = (  # pyright: ignore[reportAttributeAccessIssue]
                TM.objects.filter(Q(branches__owner__name=request.user.username))
                .annotate(branch_name=Subquery(branch_subquery))
                .distinct()
            )

    name = forms.CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Agent name",
        help_text="Create a new agent, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = forms.ModelChoiceField(
        queryset=proxies.Agent.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
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
