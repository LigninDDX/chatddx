# src/chatddx/django/repo/admin/forms/connection.py
from typing import Any, final, override

from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Column, Fieldset, Row
from django import forms
from unfold.admin import messages
from unfold.layout import Hr
from unfold.widgets import (
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminURLInputWidget,
)

from chatddx.core.choices import ProviderChoices
from chatddx.core.models import IdentityModel
from chatddx.django.portal.forms.base import BaseForm
from chatddx.repo import proxies
from chatddx.repo.form_data_in import ConnectionFormDataIn
from chatddx.repo.form_data_out import ConnectionFormDataOut


@final
class ConnectionForm(BaseForm):
    form_data_in = ConnectionFormDataIn
    form_data_out = ConnectionFormDataOut

    @final
    class Meta(BaseForm.Meta):
        model = proxies.Connection

    @override
    def save(self, commit: bool = True) -> Any:
        instance = super().save(commit=commit)
        if instance and instance.get("api_key") and self.validated_data:
            owner = IdentityModel.objects.get(name=self.request.user.username)
            owner_api_keys = owner.secrets.get("api-keys", {})
            connection_name = self.validated_data.name
            current_api_key = owner_api_keys.get(connection_name, None)

            if instance["api_key"] == current_api_key:
                messages.info(
                    self.request,
                    f"The provided API-key matches the current API-key for identity {owner.name}, all good.",
                )
            else:
                owner.secrets["api-keys"] = owner_api_keys | {
                    connection_name: instance["api_key"]
                }
                owner.save()
                messages.success(
                    self.request,
                    f"Updated API-key for identity {owner.name} and connection {connection_name}.",
                )

    name = forms.CharField(
        required=False,
        max_length=255,
        widget=UnfoldAdminTextInputWidget(),
        label="Connection name",
        help_text="Create a new connection, or enter an existing name to update it. The latest save becomes the active version.",
    )
    template = forms.ChoiceField(
        required=False,
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
    profile = forms.CharField(
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
                    Row("profile"),
                    css_class="w-1/2",
                ),
            ),
            css_class="mb-8",
        )
    )
