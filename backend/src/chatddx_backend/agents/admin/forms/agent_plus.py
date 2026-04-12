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
from chatddx_backend.agents.admin.schemas import (
    AgentFormData,
    ConnectionFormData,
    OutputTypeFormData,
    SamplingParamsFormData,
    TemplateData,
    ToolGroupFormData,
)
from chatddx_backend.agents.models import (
    AgentModel,
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
)


def model_as_dict(agent_model: AgentModel):
    agent_dict = {
        "agent": AgentFormData.model_validate(
            agent_model,
        ),
        "connection": ConnectionFormData.model_validate(
            agent_model.connection,
        ),
        "sampling_params": SamplingParamsFormData.model_validate(
            agent_model.sampling_params,
        ),
        "output_type": OutputTypeFormData.model_validate(
            agent_model.output_type,
        ),
        "tool_group": ToolGroupFormData.model_validate(
            agent_model.tool_group,
        ),
    }

    def flatten_dict(d: dict[str, Any], sep: str = "_"):
        return {
            f"{outer}{sep}{inner}": value
            for outer, inner_dict in d.items()
            for inner, value in inner_dict.model_dump().items()
        }

    return flatten_dict(agent_dict)


def get_template_data():
    return TemplateData(
        agent={
            model.pk: AgentFormData.model_validate(model)
            for model in AgentModel.objects.all()
        },
        connection={
            model.pk: ConnectionFormData.model_validate(model)
            for model in ConnectionModel.objects.all()
        },
        sampling_params={
            model.pk: SamplingParamsFormData.model_validate(model)
            for model in SamplingParamsModel.objects.all()
        },
        output_type={
            model.pk: OutputTypeFormData.model_validate(model)
            for model in OutputTypeModel.objects.all()
        },
        tool_group={
            model.pk: ToolGroupFormData.model_validate(model)
            for model in ToolGroupModel.objects.all()
        },
    ).model_dump_json()


def apply_prefix_to_layout(layout_node: LayoutObject, prefix: str):
    for i, item in enumerate(layout_node.fields):
        if isinstance(item, str):
            layout_node.fields[i] = f"{prefix}{item}"
        elif hasattr(item, "fields"):
            apply_prefix_to_layout(item, prefix)

    return layout_node


class AgentPlusForm(forms.ModelForm):
    class Media:
        js = ("js/agent_template_selector.js",)

    class Meta:
        model = proxies.Agent
        fields = []

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")

        if instance:
            kwargs["initial"] = model_as_dict(instance)

        super().__init__(*args, **kwargs)

    @property
    def helper(self):
        helper = FormHelper()

        helper.layout = Layout()
        helper.form_id = "agent_plus_form"

        sub_forms: list[
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

        for prefix, cls in sub_forms:
            sub_form_instance = cls()

            helper.layout.append(
                apply_prefix_to_layout(
                    deepcopy(sub_form_instance.helper.layout),
                    prefix,
                )
            )

            for name, field in sub_form_instance.fields.items():
                self.fields[f"{prefix}{name}"] = field

        return helper
