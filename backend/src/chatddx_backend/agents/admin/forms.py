# src/chatddx_backend/agents/admin/forms.py
from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    ModelChoiceField,
    ModelForm,
    URLField,
)
from django_json_widget.widgets import JSONEditorWidget
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminURLInputWidget,
)

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.admin.utils import serialize_trail
from chatddx_backend.agents.models import ProviderChoices
from chatddx_backend.agents.schemas import AgentSpec, ConnectionSpec


class AgentForm(ModelForm):
    template = ModelChoiceField(
        queryset=proxies.Agent.objects.none(),
        required=False,
        empty_label="--- Select a Template ---",
        widget=UnfoldAdminSelect2Widget(),
        help_text="Select a template to auto-populate the configuration below.",
    )
    make_template = BooleanField(
        required=False,
        initial=False,
        help_text="Should this configuration serve as a new template?",
    )
    connection_name = CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
    )

    connection_template = ModelChoiceField(
        queryset=proxies.Connection.objects.none(),
        required=False,
        empty_label="--- Select a Template ---",
        widget=UnfoldAdminSelect2Widget(),
        help_text="Select a template to auto-populate the configuration below.",
    )
    connection_make_template = BooleanField(
        required=False,
        initial=False,
        help_text="Should this configuration serve as a new template for other connecitons?",
    )
    model = CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
    )
    provider = ChoiceField(
        choices=ProviderChoices.choices,
        widget=UnfoldAdminSelect2Widget(),
    )
    endpoint = URLField(
        max_length=2048,
        widget=UnfoldAdminURLInputWidget(),
    )
    api_key = CharField(
        max_length=255,
        required=False,
        widget=UnfoldAdminTextInputWidget(),
    )
    profile = CharField(
        widget=UnfoldAdminExpandableTextareaWidget(),
    )

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.fields["instructions"].widget = UnfoldAdminTextareaWidget()

        qs = proxies.Agent.objects.select_related().all()
        templates = serialize_trail(AgentSpec, qs)
        self.fields["template"].queryset = qs
        self.fields["template"].widget.attrs.update(
            {
                "data-templates": templates.decode("utf-8"),
                "id": "id_template",
            }
        )

        connection_qs = proxies.Connection.objects.all()
        connection_templates = serialize_trail(ConnectionSpec, connection_qs)
        self.fields["connection_template"].queryset = connection_qs
        self.fields["connection_template"].widget.attrs.update(
            {
                "data-templates": connection_templates.decode("utf-8"),
            }
        )
        self.helper = FormHelper()
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Fieldset(
                "Primary Settings",
                Row(
                    Column(
                        Row("name"),
                        Row("make_template"),
                        css_class="col-span-6",
                    ),
                    Column("template"),
                ),
                Row(
                    Column("instructions"),
                ),
                css_class="mb-8",
            ),
            Fieldset(
                "Connection Settings",
                Row(
                    Column(
                        Row("connection_name"),
                        Row("connection_make_template"),
                    ),
                    Column("connection_template"),
                ),
                Hr(),
                Row(
                    Column(
                        Row("model"),
                        Row("endpoint"),
                        Row("api_key"),
                    ),
                    Column(
                        Row("provider"),
                        Row("profile"),
                    ),
                ),
            ),
        )

    class Meta:
        model = proxies.Agent
        fields = ["name", "instructions"]

    class Media:
        js = ("js/agent_template_selector.js",)


class ConnectionForm(ModelForm):
    class Meta:
        model = proxies.Connection
        fields = "__all__"
        widgets = {"profile": JSONEditorWidget}


class OutputTypeForm(ModelForm):
    class Meta:
        model = proxies.OutputType
        fields = "__all__"
        widgets = {"definition": JSONEditorWidget}


class SamplingParamsForm(ModelForm):
    class Meta:
        model = proxies.SamplingParams
        fields = "__all__"
        widgets = {
            "provider_params": JSONEditorWidget,
            "stop_sequences": JSONEditorWidget,
            "logit_bias": JSONEditorWidget,
        }


class ToolGroupForm(ModelForm):
    class Meta:
        model = proxies.ToolGroup
        fields = "__all__"


class IdentityForm(ModelForm):
    class Meta:
        model = proxies.Identity
        fields = "__all__"
        widgets = {"secrets": JSONEditorWidget}
