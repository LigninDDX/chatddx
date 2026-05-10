# src/chatddx_backend/models/agent.py
from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    PROTECT,
    CharField,
    DecimalField,
    ForeignKey,
    IntegerField,
    JSONField,
    PositiveIntegerField,
    TextField,
    URLField,
)

from chatddx_backend.agents.models.choices import (
    CoercionChoices,
    ProviderChoices,
    ToolChoices,
    ValidationChoices,
)
from chatddx_backend.agents.trail import RelatedArrayField, TrailModel

if TYPE_CHECKING:
    TypedJSONField = JSONField[dict[str, Any]]
else:
    TypedJSONField = JSONField


class JSONSchemaField(TypedJSONField):
    pass


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class DecimalDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(parse_float=Decimal, *args, **kwargs)


class ConnectionModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_connection"

    provider = CharField(max_length=255, choices=ProviderChoices.choices)
    model = CharField(max_length=255)
    endpoint = URLField(max_length=2048)
    profile: JSONField[dict[str, Any]] = JSONField(
        default=dict,
        blank=True,
    )


class SamplingParamsModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_sampling_params"

    temperature = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(2),
        ],
    )
    top_p = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )
    top_k = IntegerField(
        default=None,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    max_tokens = PositiveIntegerField(
        default=None,
        null=True,
        blank=True,
    )
    seed = IntegerField(
        default=None,
        null=True,
        blank=True,
    )
    n = PositiveIntegerField(
        default=None,
        null=True,
        blank=True,
    )
    presence_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
    )
    frequency_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
    )
    logit_bias: JSONField[dict[str, Decimal]] = JSONField(
        default=dict,
        blank=True,
        encoder=DecimalEncoder,
        decoder=DecimalDecoder,
    )
    provider_params: JSONField[dict[str, Any]] = JSONField(
        default=dict,
        blank=True,
    )
    stop_sequences: JSONField[list[str] | None] = JSONField(
        default=None,
        null=True,
        blank=True,
    )


class OutputTypeModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_output_type"

    definition = JSONSchemaField(
        default=dict,
    )
    validation_strategy = CharField(
        max_length=255,
        default=ValidationChoices.INFORM,
        choices=ValidationChoices.choices,
    )
    coercion_strategy = CharField(
        max_length=255,
        default=CoercionChoices.NATIVE,
        choices=CoercionChoices.choices,
    )


class ToolModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_tool"

    name = CharField(
        max_length=255,
        db_index=True,
        help_text="Name of the tool",
    )
    type = CharField(
        max_length=50,
        choices=ToolChoices.choices,
        default=ToolChoices.FUNCTION,
        help_text="The type of tool.",
    )
    description = TextField()
    parameters = JSONSchemaField()


class ToolGroupModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_tool_group"

    instructions = TextField()
    tools = RelatedArrayField(  # type: ignore
        IntegerField(),
        related_model=ToolModel,
        default=list,
    )


class AgentModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_agent"

    instructions = TextField()
    connection = ForeignKey(
        ConnectionModel,
        on_delete=PROTECT,
    )
    sampling_params = ForeignKey(
        SamplingParamsModel,
        on_delete=PROTECT,
    )
    output_type = ForeignKey(
        OutputTypeModel,
        on_delete=PROTECT,
    )
    tool_group = ForeignKey(
        ToolGroupModel,
        on_delete=PROTECT,
    )
