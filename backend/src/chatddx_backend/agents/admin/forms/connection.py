# src/chatddx_backend/agents/admin/forms/connection.py
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Column, Fieldset, Row
from django import forms
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminURLInputWidget,
)

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.models import ProviderChoices


class ConnectionForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Connection name",
        help_text="Create a new connection, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = forms.ModelChoiceField(
        queryset=proxies.Connection.objects.none(),
        required=False,
        empty_label="--- Start from scratch ---",
        widget=UnfoldAdminSelect2Widget(),
        label="Connection template",
        help_text="Optional. Select a pre-configured connection to quickly populate the API settings below.",
    )
    make_template = forms.BooleanField(
        required=False,
        initial=False,
        label="Save as template",
        help_text="Make this connection configuration available as a reusable template.",
    )
    model = forms.CharField(
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Model ID",
        help_text="The exact model identifier required by your chosen provider.",
    )
    provider = forms.ChoiceField(
        choices=ProviderChoices.choices,
        widget=UnfoldAdminSelect2Widget(),
        label="API Provider",
        help_text="The service hosting the selected model.",
    )
    endpoint = forms.URLField(
        max_length=2048,
        widget=UnfoldAdminURLInputWidget(),
        label="API Endpoint URL",
        help_text="The base URL for the provider's API.",
    )
    api_key = forms.CharField(
        max_length=255,
        required=False,
        widget=UnfoldAdminTextInputWidget(
            attrs={"placeholder": "Enter key or leave blank to use existing"}
        ),
        label="API Key",
        help_text="Stored securely under your personal user account. It is <strong>not</strong> saved in the shared version history.",
    )
    profile_toml = forms.CharField(
        widget=UnfoldAdminExpandableTextareaWidget(),
        required=False,
        label="Provider Parameters (TOML)",
        help_text="Fine-tuning parameters passed to the model, formatted as valid TOML.",
    )

    helper = FormHelper()

    helper.layout = Layout(
        Fieldset(
            "Connection Settings",
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
            Hr(),
            Row(
                Column(
                    Row("model"),
                    Row("endpoint"),
                    Row("api_key"),
                    css_class="w-1/2",
                ),
                Column(
                    Row("provider"),
                    Row("profile_toml"),
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        )
    )
