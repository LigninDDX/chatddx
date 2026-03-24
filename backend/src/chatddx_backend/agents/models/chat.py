# src/chatddx_backend/agents/models/chat.py
from __future__ import annotations

import uuid
from typing import Any, override

from django.conf import settings
from django.db.models import (
    CASCADE,
    SET_DEFAULT,
    CharField,
    DateTimeField,
    ForeignKey,
    JSONField,
    Model,
    TextField,
    UUIDField,
    manager,
)

from chatddx_backend.agents.models.enums import Role

from .agent import Agent


class Session(Model):
    uuid = UUIDField(default=uuid.uuid4, editable=False)
    description = TextField()
    agent = ForeignKey(
        Agent,
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    created_at = DateTimeField(auto_now_add=True)
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )

    messages: manager.RelatedManager[Message]

    @override
    def __str__(self):
        return self.description


class Message(Model):
    class Meta:
        ordering = ["pk"]

    role = CharField(max_length=255, choices=Role.choices)
    run_id = UUIDField(db_index=True)
    payload: JSONField[dict[str, Any]] = JSONField()
    timestamp = DateTimeField()

    session = ForeignKey(
        Session,
        related_name="messages",
        on_delete=CASCADE,
    )

    @override
    def __str__(self):
        return str(self.payload)
