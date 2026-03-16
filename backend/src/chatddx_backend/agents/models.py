# src/chatddx_backend/agents/models.py
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Self, override

import jsonref
import jsonschema
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from django.db.models import (
    CASCADE,
    SET_DEFAULT,
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    Index,
    IntegerField,
    JSONField,
    ManyToManyField,
    Model,
    PositiveIntegerField,
    TextChoices,
    TextField,
    URLField,
    UUIDField,
    manager,
)
from django.utils import timezone


def validate_json_schema(value: dict[str, Any] | None):
    if value is None:
        return
    try:
        jsonschema.Draft7Validator.check_schema(value)

        jsonref.replace_refs(value)  # type: ignore[no-untyped-call]
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid JSON Schema: {e.message}")
    except jsonref.JsonRefError as e:
        raise ValidationError(f"Invalid JSON Reference: {e.message}")


class TrailModel(Model):
    name = CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier for this record, last update is considered canon.",
    )
    fingerprint = CharField(
        max_length=64,
        db_index=True,
        unique=True,
        help_text="Fingerprint for this configuration",
    )
    created_at = DateTimeField(
        auto_now_add=True,
    )
    updated_at = DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True
        ordering = ["-updated_at"]
        get_latest_by = "updated_at"
        indexes = [
            Index(
                fields=[
                    "name",
                    "-updated_at",
                ]
            ),
        ]

    @classmethod
    def upsert_state(cls, **kwargs: Any) -> Self:
        m2m_field_names = {f.name for f in cls._meta.many_to_many}

        concrete_data = {}
        m2m_data: dict[str, list[int]] = {}

        for key, value in kwargs.items():
            if key in m2m_field_names:
                m2m_data[key] = value or []
            else:
                concrete_data[key] = value

        instance = cls(**concrete_data)

        instance.fingerprint = instance._generate_fingerprint(m2m_data)

        now = timezone.now()
        instance.updated_at = now
        instance.created_at = now

        with transaction.atomic():
            cls.objects.bulk_create(
                [instance],
                update_conflicts=True,
                unique_fields=["fingerprint"],
                update_fields=["updated_at"],
            )

            saved_instance = cls.objects.get(fingerprint=instance.fingerprint)

            if saved_instance.created_at == saved_instance.updated_at:
                for m2m_name, items in m2m_data.items():
                    getattr(saved_instance, m2m_name).set(items)

        return saved_instance

    def _generate_fingerprint(self, m2m_data: dict[str, list[Any]]) -> str:
        payload = {}
        ignore_fields = {"id", "created_at", "updated_at", "fingerprint"}

        for field in self._meta.concrete_fields:
            if field.name not in ignore_fields:
                value = getattr(self, field.attname)
                payload[field.name] = value

        for key, items in m2m_data.items():
            pks = [item.pk if hasattr(item, "pk") else item for item in items]
            payload[key] = sorted(pks)

        serialized = json.dumps(payload, sort_keys=True, cls=DjangoJSONEncoder)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class Connection(TrailModel):
    class Provider(TextChoices):
        OPENAI = "openai"
        ANTHROPIC = "anthropic"
        GOOGLE = "google"
        OLLAMA = "ollama"
        VLLM = "vllm"

    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this connection.",
    )
    provider = CharField(max_length=255, choices=Provider.choices)
    model = CharField(max_length=255)
    endpoint = URLField(max_length=255)

    @override
    def __str__(self):
        return f"{self.model}@{self.provider} ({self.endpoint})"


class Config(TrailModel):
    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this configuration.",
    )
    temperature = DecimalField(
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
    top_p = DecimalField(
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
    presence_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Penalty for using tokens that have already appeared, encouraging "
            "the model to introduce new topics (typically -2.0 to 2.0)."
        ),
    )
    frequency_penalty = DecimalField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Penalty based on how often tokens appear, reducing repetition "
            "(typically -2.0 to 2.0)."
        ),
    )
    stop_sequences = JSONField[list[str] | None](
        default=None,
        null=True,
        blank=True,
        help_text=(
            "List of strings that will stop generation when encountered.\n"
            'Examples: ["\\n\\n", "END"], ["\\"\\"\\""]'
        ),
    )
    logit_bias = JSONField[dict[str, float] | None](
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Adjusts likelihood of specific tokens appearing in the output.\n"
            "Examples: {'50256': -100} (suppress token), "
            "{'12345': 10, '67890': 5} (boost tokens)"
        ),
    )
    provider_params = JSONField[dict[str, Any] | None](
        default=None,
        null=True,
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


class Tool(TrailModel):
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
    parameters = JSONField[dict[str, Any]](
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


class Schema(TrailModel):
    name = CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for this schema.",
    )
    definition = JSONField[dict[str, Any]](
        validators=[validate_json_schema],
        help_text="A valid JSON Schema defining the expected agent response structure.",
    )

    @override
    def __str__(self):
        return self.name


class Agent(TrailModel):
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
    tools: ManyToManyField[Tool, Tool] = ManyToManyField[Tool, Tool](
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

    class Role(TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    role = CharField(max_length=255, choices=Role.choices)
    run_id = UUIDField(db_index=True)
    payload = JSONField[dict[str, Any]]()
    timestamp = DateTimeField()

    session = ForeignKey(
        Session,
        related_name="messages",
        on_delete=CASCADE,
    )

    @override
    def __str__(self):
        return str(self.payload)
