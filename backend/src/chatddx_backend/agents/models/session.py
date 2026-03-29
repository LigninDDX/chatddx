# src/chatddx_backend/agents/models/chat.py
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db.models import (
    PROTECT,
    CharField,
    DateTimeField,
    ForeignKey,
    JSONField,
    Model,
    OneToOneField,
    TextField,
    UUIDField,
    manager,
)
from encrypted_fields.fields import EncryptedJSONField

from chatddx_backend.agents.models.choices import MessageKindChoices, RoleChoices

from .agent import AgentModel


class IdentityModel(Model):
    class Meta:
        db_table = "agents_identity"

    name = CharField(max_length=255)
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


class SessionModel(Model):
    class Meta:
        db_table = "agents_session"

    uuid = UUIDField(
        default=uuid.uuid4,
        editable=False,
    )
    description = TextField(
        null=True,
        default=None,
        blank=True,
    )
    created_at = DateTimeField(auto_now_add=True)
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    default_agent = ForeignKey(
        AgentModel,
        on_delete=PROTECT,
    )

    messages: manager.RelatedManager[MessageModel]


class MessageModel(Model):
    class Meta:
        db_table = "agents_message"
        ordering = ["pk"]

    role = CharField(max_length=255, choices=RoleChoices.choices)
    kind = CharField(max_length=255, choices=MessageKindChoices.choices)
    run_id = UUIDField(db_index=True)
    payload: JSONField[dict[str, Any]] = JSONField()
    timestamp = DateTimeField()

    agent = ForeignKey(
        AgentModel,
        on_delete=PROTECT,
    )
    session = ForeignKey(
        SessionModel,
        related_name="messages",
        on_delete=PROTECT,
    )
