# src/chatddx_backend/models/agent.py
from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import jsonschema
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    PROTECT,
    CharField,
    DecimalField,
    ForeignKey,
    IntegerField,
    JSONField,
    Model,
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
    def validate(self, value: Any, model_instance: Model):
        super().validate(value, model_instance)

        if value is not None:
            try:
                jsonschema.Draft202012Validator.check_schema(value)
            except jsonschema.SchemaError as e:
                raise ValidationError(f"Invalid JSON Schema definition: {e.message}")


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
        help_text=(
            "Model-specific profile parameters fed to pydantic-ai's ModelProfile"
        ),
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
        help_text=(
            "Controls randomness in responses; higher values (>1.0) increase creativity, "
            "lower values make output more deterministic."
        ),
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
        help_text=(
            "Nucleus sampling threshold; the model considers tokens with cumulative "
            "probability up to this value (e.g., 0.9 means top 90% probable tokens)."
        ),
    )
    top_k = IntegerField(
        default=None,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=(
            "Limits sampling to the k most likely next tokens "
            "(e.g., 40 means only consider the top 40 tokens)."
        ),
    )
    max_tokens = PositiveIntegerField(
        default=None,
        null=True,
        blank=True,
        help_text="Maximum number of tokens to generate in the response.",
    )
    seed = IntegerField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Random seed for deterministic output; using the same seed with "
            "identical inputs produces consistent results."
        ),
    )
    n = PositiveIntegerField(
        default=None,
        null=True,
        blank=True,
        help_text="Number of response variations to generate for each prompt.",
    )
    presence_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
        help_text=(
            "Penalty for using tokens that have already appeared, encouraging "
            "the model to introduce new topics (typically -2.0 to 2.0)."
        ),
    )
    frequency_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
        help_text=(
            "Penalty based on how often tokens appear, reducing repetition "
            "(typically -2.0 to 2.0)."
        ),
    )
    logit_bias: JSONField[dict[str, Decimal]] = JSONField(
        default=dict,
        blank=True,
        encoder=DecimalEncoder,
        decoder=DecimalDecoder,
        help_text=(
            "Adjusts likelihood of specific tokens appearing in the output.\n"
            "Examples: {'50256': -100} (suppress token), "
            "{'12345': 10, '67890': 5} (boost tokens)"
        ),
    )
    provider_params: JSONField[dict[str, Any]] = JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Provider-specific parameters not covered by standard fields.\n"
            'Examples: {"response_format": {"type": "json_object"}}, '
            '{"anthropic_version": "2023-06-01", "thinking": {"type": "enabled"}}'
        ),
    )
    stop_sequences: JSONField[list[str] | None] = JSONField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "List of strings that will stop generation when encountered.\n"
            'Examples: ["\\n\\n", "END"], ["\\"\\"\\""]'
        ),
    )


class OutputTypeModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_output_type"

    definition = JSONSchemaField(
        help_text="A valid JSON Schema defining the expected agent response structure.",
    )


class ToolModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_tool"

    type = CharField(
        max_length=50,
        choices=ToolChoices.choices,
        default=ToolChoices.FUNCTION,
        help_text="The type of tool.",
    )
    description = TextField(
        default=None,
        null=True,
        blank=True,
    )
    parameters = JSONSchemaField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "JSON Schema describing the tool's parameters.\n"
            'Example: {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'
        ),
    )


class ToolGroupModel(TrailModel):
    class Meta(TrailModel.Meta):
        db_table = "agents_tool_group"

    instructions = TextField()
    tools = RelatedArrayField(  # type: ignore
        IntegerField(),
        related_model=ToolModel,
        default=list,
        help_text="Snapshot of tool pks attached to this configuration version.",
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
