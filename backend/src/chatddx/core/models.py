from typing import Any

from django.conf import settings
from django.db.models import PROTECT, CharField, Model, OneToOneField, UUIDField
from encrypted_fields import EncryptedJSONField


class IdentityModel(Model):
    class Meta:
        app_label = "orm"
        db_table = "agents_identity"

    name = CharField(
        max_length=255,
        unique=True,
    )
    secrets: dict[str, Any] = EncryptedJSONField(default=dict)  # type: ignore[assignment]
    guest_id = UUIDField(
        default=None,
        null=True,
        blank=True,
    )
    auth_user = OneToOneField(
        settings.AUTH_USER_MODEL,
        default=None,
        null=True,
        blank=True,
        on_delete=PROTECT,
    )
