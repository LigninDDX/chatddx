# src/chatddx/django/repo/admin/forms/agent.py
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django import forms
from django.db.models import OuterRef, Q, Subquery
from repo.admin import proxies
from repo.admin.base import branch_map
from repo.admin.forms.base import BaseForm
from repo.models import (
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
)
from repo.models.loader import agent_relations
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx.django.repo.admin.schemas import AgentFormData


class AgentForm(BaseForm):
    form_data = AgentFormData

    class Meta(BaseForm.Meta):
        model = proxies.Agent

    def __init__(self, *args: Any, **kwargs: Any):
        self.is_subform = kwargs.get("is_subform")

        if self.is_subform:
            super().__init__(*args, **kwargs)
            return

        request = kwargs["request"]
        super().__init__(*args, **kwargs)

        for field_name in agent_relations:
            TrailModel = branch_map[field_name][2]
            branch_subquery = TrailModel.objects.filter(pk=OuterRef("pk")).values(
                "branches__name"
            )[:1]

            self.fields[field_name + "_id"].queryset = (  # pyright: ignore[reportAttributeAccessIssue]
                TrailModel.objects.filter(
                    Q(agentmodel__branches__owner__name=request.user.username)
                    | Q(branches__owner__name=request.user.username)
                )
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
    connection_id = forms.ModelChoiceField(
        queryset=ConnectionModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Connection",
    )
    sampling_params_id = forms.ModelChoiceField(
        queryset=SamplingParamsModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Sampling Parameters",
    )
    output_type_id = forms.ModelChoiceField(
        queryset=OutputTypeModel.objects.none(),
        widget=UnfoldAdminSelect2Widget(),
        label="Output Type",
    )
    tool_group_id = forms.ModelChoiceField(
        queryset=ToolGroupModel.objects.none(),
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
                    "connection_id",
                    "sampling_params_id",
                    css_class="w-1/2",
                ),
                Column(
                    "output_type_id",
                    "tool_group_id",
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        )

        if self.is_subform:
            pass

        helper.layout = Layout(main_section, relations_section)

        return helper
