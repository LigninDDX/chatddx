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

from chatddx_backend.agents.models.enums import RoleChoices

from .agent import Agent


class User(Model):
    auth_user = OneToOneField(settings.AUTH_USER_MODEL, on_delete=PROTECT)
    default_agent = ForeignKey(Agent, on_delete=PROTECT)


class Session(Model):
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
    user = ForeignKey(
        User,
        on_delete=PROTECT,
    )
    default_agent = ForeignKey(
        Agent,
        on_delete=PROTECT,
    )

    messages: manager.RelatedManager[Message]


class Message(Model):
    class Meta:
        ordering = ["pk"]

    role = CharField(max_length=255, choices=RoleChoices.choices)
    run_id = UUIDField(db_index=True)
    payload: JSONField[dict[str, Any]] = JSONField()
    timestamp = DateTimeField()

    agent = ForeignKey(
        Agent,
        null=True,
        default=None,
        on_delete=PROTECT,
    )
    session = ForeignKey(
        Session,
        related_name="messages",
        on_delete=PROTECT,
    )
