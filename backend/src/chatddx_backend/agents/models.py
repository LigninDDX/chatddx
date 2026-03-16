# src/chatddx_backend/agents/models.py
from __future__ import annotations

import uuid
from typing import Any, Iterable, Self, Tuple, override

import jsonref
import jsonschema
from django.conf import settings
from django.contrib.postgres.fields.array import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import DatabaseError, connection
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
    Model,
    PositiveIntegerField,
    TextChoices,
    TextField,
    URLField,
    UUIDField,
    manager,
)
from django.utils import timezone

from chatddx_backend.agents.utils import camel_to_snake

DjangoChoices = Iterable[Tuple[Any, str]]


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


class RelatedArrayField(ArrayField):  # type: ignore[type-arg]
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        return super().__new__(cls)  # type: ignore[call-overload]

    def __init__(
        self,
        *args: Any,
        related_model: type[TrailModel],
        **kwargs: Any,
    ) -> None:
        self.related_model: type[TrailModel] = related_model
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["related_model"] = self.related_model
        return name, path, args, kwargs


class TrailModel(Model):
    name = CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier for this record, last update is considered canon.",
    )
    fingerprint = CharField(
        max_length=64,
        db_index=True,
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
        unique_together = (("name", "fingerprint"),)
        indexes = [
            Index(
                fields=[
                    "name",
                    "-updated_at",
                ]
            ),
        ]

    @classmethod
    def record_name(cls) -> str:
        return camel_to_snake(cls.__name__)

    @classmethod
    def upsert(cls, **kwargs: Any) -> Self:
        concrete_data = {}

        for key, value in kwargs.items():
            concrete_data[key] = value

        return cls.objects.get(
            pk=cls(**concrete_data).resolve(),
        )

    def resolve(self) -> Self:
        ignore_fields = {"id", "name", "created_at", "updated_at", "fingerprint"}

        db_fields: list[str] = []
        db_values: list[Any] = []

        hash_values: list[Any] = []
        jsonb_args: list[str] = []

        now = timezone.now()
        self.updated_at = now
        self.created_at = now

        for field in self._meta.concrete_fields:
            if field.primary_key:
                continue

            value = field.get_db_prep_save(getattr(self, field.attname), connection)

            if field.name not in ignore_fields:
                hash_values.append(value)
                jsonb_args.append(f"'{field.column}'")

                if isinstance(field, DecimalField):
                    jsonb_args.append(
                        f"%s::numeric({field.max_digits}, {field.decimal_places})"
                    )
                else:
                    jsonb_args.append("%s")

            if field.name != "fingerprint":
                db_fields.append(field.column)
                db_values.append(value)

        qn = connection.ops.quote_name
        table_name = qn(self._meta.db_table)

        jsonb_expr = f"jsonb_build_object({', '.join(jsonb_args)})"

        fingerprint_expr = f"encode(sha256(CAST({jsonb_expr} AS text)::bytea), 'hex')"

        all_insert_cols = db_fields + ["fingerprint"]
        field_names = ", ".join(qn(f) for f in all_insert_cols)

        placeholders_list = ["%s"] * len(db_fields)
        placeholders_list.append(fingerprint_expr)
        placeholders = ", ".join(placeholders_list)

        final_values = db_values + hash_values

        conflict_target = qn("name") + ", " + qn("fingerprint")
        update_col = qn("updated_at")

        sql = f"""
            INSERT INTO {table_name} ({field_names})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_target})
            DO UPDATE SET {update_col} = EXCLUDED.{update_col}
            RETURNING id, fingerprint, (xmax = 0) AS is_created;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, final_values)
            result = cursor.fetchone()

            if not result:
                raise DatabaseError("Upsert failed: No rows returned from Postgres.")

        pk, fingerprint, is_created = result
        self.pk = pk
        self.fingerprint = fingerprint

        return pk

    @override
    def __str__(self):
        return self.name


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
