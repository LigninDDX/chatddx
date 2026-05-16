# src/chatddx_backend/agents/admin/forms/super_agent.py
from copy import deepcopy
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, LayoutObject
from django import forms

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.admin.forms import (
    AgentForm,
    ConnectionForm,
    OutputTypeForm,
    SamplingParamsForm,
    ToolGroupForm,
)
from chatddx_backend.agents.models.history import AgentBranchModel

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

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")
        request = kwargs.pop("request")
        self.sub_forms = {}

        if instance:
            kwargs["initial"] = self.get_initial(instance)

        super().__init__(*args, **kwargs)

        for prefix, cls in SUB_FORMS:
            self.sub_forms[prefix] = cls(
                is_subform=True,
                request=request,
            )

            for _name, _field in self.sub_forms[prefix].fields.items():
                name = f"{prefix}{_name}"
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

        def flatten_dict(d: dict[str, Any]):
            return {
                f"{outer}{inner}": value
                for outer, inner_dict in d.items()
                for inner, value in inner_dict.items()
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
