# src/chatddx/django/portal/forms/super_agent.py
from copy import deepcopy
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, LayoutObject
from django import forms
from django.http import HttpRequest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from chatddx.django.portal.forms.agent import AgentForm
from chatddx.django.portal.forms.connection import ConnectionForm
from chatddx.django.portal.forms.output_type import OutputTypeForm
from chatddx.django.portal.forms.sampling_params import SamplingParamsForm
from chatddx.django.portal.forms.tool_group import ToolGroupForm
from chatddx.repo import proxies
from chatddx.repo.branch_models import AgentBranchModel
from chatddx.repo.loaders.branches import get_branch_model
from chatddx.repo.loaders.model_loader import agent_relations
from chatddx.utils import flatten_dict, unflatten_dict

OPTIONAL_FIELDS = {
    "connection_name",
    "sampling_params_name",
    "output_type_name",
    "tool_group_name",
}

SUB_FORMS: list[
    tuple[
        str,
        type[
            AgentForm
            | ConnectionForm
            | SamplingParamsForm
            | OutputTypeForm
            | ToolGroupForm
        ],
    ]
] = [
    ("agent_", AgentForm),
    ("connection_", ConnectionForm),
    ("sampling_params_", SamplingParamsForm),
    ("output_type_", OutputTypeForm),
    ("tool_group_", ToolGroupForm),
]


def apply_prefix_to_layout(layout_node: LayoutObject, prefix: str):
    for i, item in enumerate(layout_node.fields):
        if isinstance(item, str):
            layout_node.fields[i] = f"{prefix}{item}"
        elif hasattr(item, "fields"):
            apply_prefix_to_layout(item, prefix)

    return layout_node


class SuperAgentForm(forms.ModelForm):
    class Meta:
        model = proxies.Agent
        fields = []

    form_data: BaseModel
    model_name: str
    request: HttpRequest

    def clean(self):
        cleaned_data = super().clean()

        data = unflatten_dict(cleaned_data, agent_relations + ["agent"])
        agent_data = data.pop("agent")
        owner_name = self.request.user.username

        for relation_name, relation_data in data.items():
            try:
                relation_obj = get_branch_model(
                    relation_name, owner_name, relation_data
                )
            except PydanticValidationError as e:
                for error in e.errors():
                    self.add_error(
                        f"{relation_name}_{error['loc'][0]}",
                        error["msg"],
                    )
                return

            if not relation_obj.pk and relation_obj.name:
                relation_obj.save()

            agent_data[relation_name + "_id"] = relation_obj.target.pk

        try:
            self.actual_obj = get_branch_model(
                "agent",
                self.request.user.username,
                agent_data,
            )
        except PydanticValidationError as e:
            for error in e.errors():
                self.add_error(
                    f"agent_{error['loc'][0]}",
                    error["msg"],
                )
            return

        return agent_data

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        self.request = kwargs.pop("request")
        self.model_name = kwargs.pop("model_name")
        self.sub_forms = {}

        if instance:
            kwargs["initial"] = self.get_initial(instance)

        super().__init__(*args, **kwargs)

        if self.data:
            self.data = self.data.copy()
            self.data.pop("agent_template", None)
            for field_name in agent_relations:
                self.data.pop(f"{field_name}_template", None)

        ignore_fields = [f"agent_{relation}_id" for relation in agent_relations]

        for prefix, cls in SUB_FORMS:
            self.sub_forms[prefix] = cls(
                is_subform=True,
                request=self.request,
            )

            for _name, _field in self.sub_forms[prefix].fields.items():
                name = f"{prefix}{_name}"
                if name in ignore_fields:
                    continue
                field = deepcopy(_field)

                if name in OPTIONAL_FIELDS:
                    field.required = False

                self.fields[name] = field

    @classmethod
    def get_initial(cls, agent_model: AgentBranchModel):
        agent_dict = {
            "agent_": AgentForm.get_initial(
                agent_model.target,
                agent_model.name,
            ),
            "connection_": ConnectionForm.get_initial(
                agent_model.target.connection,
                agent_model.connection_name,
            ),
            "sampling_params_": SamplingParamsForm.get_initial(
                agent_model.target.sampling_params,
                agent_model.sampling_params_name,
            ),
            "output_type_": OutputTypeForm.get_initial(
                agent_model.target.output_type,
                agent_model.output_type_name,
            ),
            "tool_group_": ToolGroupForm.get_initial(
                agent_model.target.tool_group,
                agent_model.tool_group_name,
            ),
        }

        return flatten_dict(agent_dict)

    @property
    def helper(self):
        helper = FormHelper()

        helper.layout = Layout()
        helper.form_tag = False
        helper.include_media = False

        for prefix, _ in SUB_FORMS:
            sub_form_instance = self.sub_forms[prefix]

            helper.layout.append(
                apply_prefix_to_layout(
                    deepcopy(sub_form_instance.helper.layout[0]),
                    prefix,
                )
            )

        return helper
