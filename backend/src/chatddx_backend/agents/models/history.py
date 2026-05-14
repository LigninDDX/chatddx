# src/chatddx_backend/agents/models/history.py
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db.models import (
    PROTECT,
    CharField,
    DateTimeField,
    ForeignKey,
    Index,
    JSONField,
    Model,
    OneToOneField,
    TextField,
    UUIDField,
    manager,
)
from encrypted_fields.fields import EncryptedJSONField

from chatddx_backend.agents.models.choices import MessageKindChoices, RoleChoices

from .agent import (
    AgentModel,
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
    ToolModel,
)


class IdentityModel(Model):
    class Meta:
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


class BranchModel(Model):
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    name = CharField(max_length=255)
    timestamp = DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        abstract = True
        indexes = [
            Index(fields=["owner", "name", "-timestamp"]),
        ]


class AgentBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_agent_branch"

    target = ForeignKey(
        AgentModel,
        on_delete=PROTECT,
        related_name="branches",
    )


class ConnectionBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_connection_branch"

    target = ForeignKey(
        ConnectionModel,
        on_delete=PROTECT,
        related_name="branches",
    )


class SamplingParamsBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_sampling_params_branch"

    target = ForeignKey(
        SamplingParamsModel,
        on_delete=PROTECT,
        related_name="branches",
    )


class ToolGroupBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_tool_group_branch"

    target = ForeignKey(
        ToolGroupModel,
        on_delete=PROTECT,
        related_name="branches",
    )


class ToolBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_tool_branch"

    target = ForeignKey(
        ToolModel,
        on_delete=PROTECT,
        related_name="branches",
    )


class OutputTypeBranchModel(BranchModel):
    class Meta(BranchModel.Meta):
        db_table = "agents_output_type_branch"

    target = ForeignKey(
        OutputTypeModel,
        on_delete=PROTECT,
        related_name="branches",
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
    timestamp = DateTimeField(auto_now_add=True)
    owner = ForeignKey(
        IdentityModel,
        on_delete=PROTECT,
    )
    default_agent = ForeignKey(
        AgentBranchModel,
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
