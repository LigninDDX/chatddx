from django.core.validators import MaxValueValidator, MinValueValidator
from typing import override, TypeVar, Generic, Type, cast

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
from pydantic import BaseModel
from chatddx_backend.api.result_schemas import SCHEMA_REGISTRY, UserProfile

T = TypeVar("T", bound=BaseModel)


class Connection(Model):
    class Provider(TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GOOGLE = "google", "Google"

    class Model(TextChoices):
        llama = "llama", "llama"

    provider = CharField(max_length=255, choices=Provider.choices)
    model = CharField(max_length=255, choices=Model.choices)
    endpoint = URLField(max_length=255)

    api_key_identifier = CharField(
        default=None,
        null=True,
        blank=True,
        max_length=255,
    )

    @override
    def __str__(self):
        return f"{self.model}@{self.provider}"


class Config(Model):
    name = CharField(max_length=255, unique=True)

    temperature = FloatField(
        default=None,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(2),
        ],
    )

    top_p = FloatField(
        default=None,
        null=True,
        blank=True,
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

    seed = IntegerField(default=None, null=True, blank=True)
    stream = BooleanField(default=False)
    n = PositiveIntegerField(default=1)

    presence_penalty = FloatField(default=0.0)
    frequency_penalty = FloatField(default=0.0)

    stop_sequences = JSONField(default=list, blank=True)
    logit_bias = JSONField(
        default=dict, blank=True, help_text="Format: {'token_id': bias_value}"
    )
    provider_params = JSONField(default=dict, blank=True)

    @override
    def __str__(self):
        return self.name


class Tool(Model):
    name = CharField(max_length=255, unique=True)
    description = TextField()
    parameters = JSONField()

    @override
    def __str__(self):
        return self.name


class Agent(Model, Generic[T]):
    name = CharField(max_length=255, unique=True)
    connection = ForeignKey(
        Connection,
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
        on_delete=PROTECT,
    )

    system_prompt = TextField()

    output_type_name = CharField(
        max_length=255,
        choices=[
            (name, name.replace("_", " ").title()) for name in SCHEMA_REGISTRY.keys()
        ],
        help_text="Pydantic schema for structured output validation",
    )

    tools = ManyToManyField(Tool, blank=True)
    tool_choice = JSONField(default=None, null=True, blank=True)

    @property
    def output_type(self) -> Type[T]:
        return cast(Type[T], SCHEMA_REGISTRY[self.output_type_name])

    @override
    def __str__(self):
        return self.name


class UserProfileAgent(Agent):
    class Meta:
        proxy: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_type_name = "UserProfile"

    def save(self, *args, **kwargs):
        self.output_type_name = "UserProfile"
        super().save(*args, **kwargs)

    @property
    @override
    def output_type(self) -> Type[UserProfile]:
        return UserProfile


class Session(Model):
    title = CharField(max_length=255, unique=True)
    agent = ForeignKey(Agent, on_delete=PROTECT)
    started_at = DateTimeField(auto_now_add=True)

    @override
    def __str__(self):
        return self.title


class Message(Model):
    class Meta:
        ordering: list[str] = ["sequence"]
        unique_together: list[list[str]] = [["session", "sequence"]]

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
