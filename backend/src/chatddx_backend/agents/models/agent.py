# src/chatddx_backend/models/agent.py
from __future__ import annotations

from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    SET_DEFAULT,
    BooleanField,
    CharField,
    DecimalField,
    ForeignKey,
    IntegerField,
    JSONField,
    PositiveIntegerField,
    TextChoices,
    TextField,
    URLField,
)

from .trail import RelatedArrayField, TrailModel
from .validators import validate_json_schema


class Connection(TrailModel):
    class Provider(TextChoices):
        OPENAI = "openai"
        ANTHROPIC = "anthropic"
        GOOGLE = "google"
        OLLAMA = "ollama"
        VLLM = "vllm"

    provider = CharField(max_length=255, choices=Provider.choices)
    model = CharField(max_length=255)
    endpoint = URLField(max_length=2048)


class SamplingParams(TrailModel):
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
    logit_bias: JSONField[dict[str, float]] = JSONField(
        default=dict,
        blank=True,
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
    # None = don't touch
    # [] = actively clear stop sequences upstream
    stop_sequences: JSONField[list[str] | None] = JSONField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "List of strings that will stop generation when encountered.\n"
            'Examples: ["\\n\\n", "END"], ["\\"\\"\\""]'
        ),
    )


class Schema(TrailModel):
    definition: JSONField[dict[str, Any]] = JSONField(
        validators=[validate_json_schema],
        help_text="A valid JSON Schema defining the expected agent response structure.",
    )


class Tool(TrailModel):
    class ToolType(TextChoices):
        FUNCTION = "function", "Function"
        CODE_INTERPRETER = "code_interpreter", "Code Interpreter"
        FILE_SEARCH = "file_search", "File Search"
        WEB_SEARCH = "web_search", "Web Search"

    description = TextField()
    type = CharField(
        max_length=50,
        choices=ToolType.choices,
        default=ToolType.FUNCTION,
        help_text="The type of tool.",
    )
    parameters: JSONField[dict[str, Any]] = JSONField(
        default=dict,
        blank=True,
        help_text=(
            "JSON Schema describing the tool's parameters.\n"
            'Example: {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'
        ),
    )


class ToolGroup(TrailModel):
    instructions = TextField()

    tools = RelatedArrayField(
        IntegerField(),
        related_model=Tool,
        blank=True,
        default=list,
        help_text="Snapshot of tool IDs attached to this configuration version.",
    )


class Agent(TrailModel):
    class ValidationStrategy(TextChoices):
        NOOP = "noop"
        RETRY = "retry"
        INFORM = "inform"
        CRASH = "crash"

    class CoercionStrategy(TextChoices):
        PROMPTED = "prompted"
        TOOL = "tool"
        NATIVE = "native"

    instructions = TextField()
    connection = ForeignKey(
        Connection,
        related_name="agents",
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    sampling_params = ForeignKey(
        SamplingParams,
        related_name="agents",
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    schema = ForeignKey(
        Schema,
        related_name="agents",
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    tool_group = ForeignKey(
        ToolGroup,
        related_name="agents",
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    use_tools = BooleanField(
        default=False,
    )
    # Cannot be None; use ValidationStrategy.NOOP to explicitly disable
    validation_strategy = CharField(
        max_length=255,
        default=ValidationStrategy.INFORM,
        choices=ValidationStrategy.choices,
    )
    # None = defer to upstream default; bypasses use_tools when set to TOOL.
    coercion_strategy = CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
        choices=CoercionStrategy.choices,
    )
