from __future__ import annotations

from typing import override

import jsonref
import jsonschema
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_DEFAULT,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    IntegerField,
    JSONField,
    ManyToManyField,
    Model,
    PositiveIntegerField,
    TextChoices,
    TextField,
    URLField,
)


def validate_json_schema(value):
    if value is None:
        return
    try:
        jsonschema.Draft7Validator.check_schema(value)
        jsonref.replace_refs(value)
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid JSON Schema: {e.message}")
    except jsonref.JsonRefError as e:
        raise ValidationError(f"Invalid JSON Reference: {e.message}")


class Connection(Model):
    class Provider(TextChoices):
        OPENAI = "openai"
        ANTHROPIC = "anthropic"
        GOOGLE = "google"
        OLLAMA = "ollama"
        VLLM = "vllm"

    provider = CharField(max_length=255, choices=Provider.choices)
    model = CharField(max_length=255)
    endpoint = URLField(max_length=255)

    @override
    def __str__(self):
        return f"{self.model}@{self.provider} ({self.endpoint})"


class Config(Model):
    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this configuration.",
    )
    temperature = FloatField(
        default=None,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(2),
        ],
        help_text=(
            "Controls randomness in responses; higher values (>1.0) increase creativity, "
            "lower values make output more deterministic."
        ),
    )
    top_p = FloatField(
        default=None,
        null=True,
        blank=True,
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
    presence_penalty = FloatField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Penalty for using tokens that have already appeared, encouraging "
            "the model to introduce new topics (typically -2.0 to 2.0)."
        ),
    )
    frequency_penalty = FloatField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Penalty based on how often tokens appear, reducing repetition "
            "(typically -2.0 to 2.0)."
        ),
    )
    stop_sequences = JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of strings that will stop generation when encountered.\n"
            'Examples: ["\\n\\n", "END"], ["\\"\\"\\""]'
        ),
    )
    logit_bias = JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Adjusts likelihood of specific tokens appearing in the output.\n"
            "Examples: {'50256': -100} (suppress token), "
            "{'12345': 10, '67890': 5} (boost tokens)"
        ),
    )
    provider_params = JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Provider-specific parameters not covered by standard fields.\n"
            'Examples: {"response_format": {"type": "json_object"}}, '
            '{"anthropic_version": "2023-06-01", "thinking": {"type": "enabled"}}'
        ),
    )

    @override
    def __str__(self):
        return self.name


class Tool(Model):
    class ToolType(TextChoices):
        FUNCTION = "function", "Function"
        CODE_INTERPRETER = "code_interpreter", "Code Interpreter"
        FILE_SEARCH = "file_search", "File Search"
        WEB_SEARCH = "web_search", "Web Search"

    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this tool.",
    )
    type = CharField(
        max_length=50,
        choices=ToolType.choices,
        default=ToolType.FUNCTION,
        help_text="The type of tool.",
    )
    parameters = JSONField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "JSON Schema describing the tool's parameters.\n"
            'Example: {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'
        ),
    )

    @override
    def __str__(self):
        return self.name


class Schema(Model):
    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this schema.",
    )
    definition = JSONField(
        validators=[validate_json_schema],
        help_text="A valid JSON Schema defining the expected agent response structure.",
    )

    @override
    def __str__(self):
        return self.name


class Agent(Model):
    class ValidationStrategy(TextChoices):
        NONE = "none"
        RETRY = "retry"
        INFORM = "inform"
        CRASH = "crash"

    class CoercionStrategy(TextChoices):
        PROMPTED = "prompted"
        TOOL = "tool"
        NATIVE = "native"

    name = CharField(max_length=255, unique=True)
    instructions = TextField()
    connection = ForeignKey(
        Connection,
        related_name="agents",
        default=None,
        null=True,
        blank=True,
        on_delete=SET_DEFAULT,
    )
    config = ForeignKey(
        Config,
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
    tools = ManyToManyField(
        Tool,
        blank=True,
    )
    use_tools = BooleanField(
        default=False,
    )
    validation_strategy = CharField(
        max_length=255,
        default=ValidationStrategy.INFORM,
        choices=ValidationStrategy.choices,
    )
    coercion_strategy = CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
        choices=CoercionStrategy.choices,
    )

    @override
    def __str__(self):
        return self.name


class Session(Model):
    title = CharField(max_length=255, unique=True)
    agent = ForeignKey(Agent, on_delete=PROTECT)
    started_at = DateTimeField(auto_now_add=True)

    @override
    def __str__(self):
        return self.title


class Message(Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = [["session", "sequence"]]

    class Role(TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"
        DEVELOPER = "developer", "Developer"
        THOUGHT = "thought", "Thought"
        REASONING = "reasoning", "Reasoning"

    role = CharField(max_length=32, choices=Role.choices)
    payload = JSONField()
    created_at = DateTimeField(auto_now_add=True)
    sequence = PositiveIntegerField()

    session = ForeignKey(
        Session,
        related_name="messages",
        on_delete=CASCADE,
    )

    @override
    def __str__(self):
        return self.payload[:100]
