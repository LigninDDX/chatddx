# pyright: basic
from __future__ import annotations

import uuid
from typing import Any

from django.db.models import (
    PROTECT,
    SET_DEFAULT,
    CharField,
    DateTimeField,
    ForeignKey,
    JSONField,
    ManyToManyField,
    Model,
    QuerySet,
    UUIDField,
)

from chatddx.core.choices import MessageKindChoices, RoleChoices
from chatddx.core.models import IdentityModel
from chatddx.repo.branch_models import AgentBranchModel
from chatddx.repo.trail_models import AgentTrailModel


class SessionModel(Model):
    class Meta:
        app_label = "orm"
        db_table = "agents_session"

    uuid = UUIDField(
        default=uuid.uuid4,
        editable=False,
    )
    description = CharField(
        max_length=255,
        null=True,
        default=None,
        blank=True,
    )
    timestamp = DateTimeField(auto_now_add=True)
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    default_agent = ForeignKey(
        AgentBranchModel,
        default=None,
        null=True,
        on_delete=SET_DEFAULT,
    )
    collaborators = ManyToManyField(
        IdentityModel,
        blank=True,
        related_name="shared_sessions",
    )

    messages: QuerySet[MessageModel]


class MessageModel(Model):
    class Meta:
        app_label = "orm"
        db_table = "agents_message"
        ordering = ["pk"]

    role = CharField(max_length=255, choices=RoleChoices.choices)
    kind = CharField(max_length=255, choices=MessageKindChoices.choices)
    run_id = UUIDField(db_index=True)
    payload: JSONField[dict[str, Any]] = JSONField()
    timestamp = DateTimeField()

    agent = ForeignKey(
        AgentTrailModel,
        on_delete=PROTECT,
    )
    session = ForeignKey(
        SessionModel,
        related_name="messages",
        on_delete=PROTECT,
    )
