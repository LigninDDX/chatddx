# src/chatddx_backend/agents/admin/forms/connection.py
from typing import Any

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
from chatddx_backend.agents.admin.schemas import ConnectionFormData
from chatddx_backend.agents.models import ProviderChoices


class ConnectionForm(forms.ModelForm):
    class Meta:
        model = proxies.Connection
        fields = []

    def __init__(self, *args: Any, **kwargs: Any):
        instance = kwargs.get("instance")

        if instance:
            kwargs["initial"] = self.get_initial(instance.target, instance.name)

        super().__init__(*args, **kwargs)

    @classmethod
    def get_initial(cls, trail_model, name=None):
        return ConnectionFormData.model_validate(
            trail_model,
            context={"name": name},
        ).model_dump()

    name = forms.CharField(
        required=False,
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
        label="Prefill from existing",
        help_text="Optional. Select a pre-configured connection to quickly populate the API settings below.",
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
    helper.form_tag = False
    helper.include_media = False

    helper.layout = Layout(
        Fieldset(
            "Connection Settings",
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
