# src/chatddx/django/portal/forms/super_agent.py
from copy import deepcopy
from typing import Any, final, override

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, LayoutObject, Row
from django import forms
from django.http.request import QueryDict
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
)

from chatddx.django.portal.forms.base import BaseForm
from chatddx.django.portal.forms.connection import ConnectionForm
from chatddx.django.portal.forms.output_type import OutputTypeForm
from chatddx.django.portal.forms.sampling_params import SamplingParamsForm
from chatddx.django.portal.forms.tool_group import ToolGroupForm
from chatddx.repo import proxies
from chatddx.repo.branch_models import AgentBranchModel
from chatddx.repo.form_data_in import SuperAgentFormDataIn
from chatddx.repo.form_data_out import SuperAgentFormDataOut
from chatddx.repo.main import BundleName
from chatddx.repo.shufflers.main import agent_relations

OPTIONAL_FIELDS = {
    "connection_name",
    "sampling_params_name",
    "output_type_name",
    "tool_group_name",
}

SUBFORMS: list[tuple[BundleName, type[BaseForm]]] = [
    ("connection", ConnectionForm),
    ("sampling_params", SamplingParamsForm),
    ("output_type", OutputTypeForm),
    ("tool_group", ToolGroupForm),
]


def apply_prefix_to_layout(layout_node: LayoutObject, prefix: str):
    for i, item in enumerate(layout_node.fields):
        if isinstance(item, str):
            layout_node.fields[i] = prefixed(item, prefix)
        elif hasattr(item, "fields"):
            apply_prefix_to_layout(item, prefix)

    return layout_node


def prefixed(name: str, prefix: str):
    return f"{prefix}_{name}"


def unprefixed(name: str, prefix: str):
    return name[len(prefix) + 1 :]


def get_subform_data(data: QueryDict, prefix: str) -> QueryDict | None:
    if not data:
        return None
    result = QueryDict(mutable=True)
    for k, vals in data.lists():
        if k.startswith(prefix):
            result.setlist(unprefixed(k, prefix), vals)
    return result


def flatten_form_data(data: dict[str, Any]):
    return {
        prefixed(field_name, prefix): value
        for prefix, subform in data.items()
        for field_name, value in subform.items()
    }


@final
class SuperAgentForm(BaseForm):
    @final
    class Meta(BaseForm.Meta):
        model = proxies.Agent

    form_data_in = SuperAgentFormDataIn
    form_data_out = SuperAgentFormDataOut

    subforms: dict[BundleName, BaseForm]

    @override
    def clean(self):
        for subform_name, subform_instance in self.subforms.items():
            is_valid = subform_instance.is_valid()
            self.cleaned_data[subform_name] = subform_instance.clean()
            if not is_valid:
                for field_name, error_messages in subform_instance.errors.items():
                    for error_msg in error_messages:
                        self.add_error(prefixed(field_name, subform_name), error_msg)

        cleaned = super().clean()
        return cleaned

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        self.subforms = {}
        self._request = kwargs["request"]

        if instance:
            kwargs["initial"] = self.get_super_initial(instance)

        super().__init__(*args, **kwargs)

        if self.data:
            self.data = self.data.copy()
            self.data.pop("agent_template", None)
            for field_name in agent_relations:
                self.data.pop(f"{field_name}_template", None)

        for prefix, cls in SUBFORMS:
            sub_form_data = get_subform_data(self.data, prefix)
            self.subforms[prefix] = cls(
                data=sub_form_data,
                request=self._request,
            )
            for _name, _field in self.subforms[prefix].fields.items():
                name = prefixed(_name, prefix)
                field = deepcopy(_field)

                if name in OPTIONAL_FIELDS:
                    field.required = False

                self.fields[name] = field

    @classmethod
    def get_super_initial(cls, super_agent: AgentBranchModel):
        agent_dict = super().get_initial(super_agent.target, super_agent.name)
        relations_dict = {
            prefix: cls.get_initial(
                getattr(super_agent.target, prefix),
                getattr(super_agent, prefixed("name", prefix)),
            )
            for prefix, cls in SUBFORMS
        }

        return agent_dict | flatten_form_data(relations_dict)

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

        helper.layout = Layout(main_section)
        for prefix, _ in SUBFORMS:
            subform_instance = self.subforms[prefix]

            helper.layout.append(
                apply_prefix_to_layout(
                    deepcopy(subform_instance.helper.layout[0]),
                    prefix,
                )
            )

        return helper
