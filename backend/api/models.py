from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import (
    CASCADE,
    PROTECT,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    OneToOneField,
    PositiveIntegerField,
    TextChoices,
    TextField,
)


class OpenAIMessageRole(Model):
    class Meta:
        verbose_name_plural = "OpenAI Message Roles"

    def __str__(self):
        return str(self.name)

    name = CharField(max_length=255)


class OpenAIModel(Model):
    class Meta:
        verbose_name_plural = "OpenAI Models"

    def __str__(self):
        return str(self.name)

    name = CharField(max_length=255)


class OpenAILogitBias(Model):
    class Meta:
        verbose_name_plural = "OpenAI Logit Biases"

    def __str__(self):
        return f"{self.token} ({self.bias})"

    token = CharField(max_length=255)
    bias = IntegerField(
        validators=[
            MaxValueValidator(100),
            MinValueValidator(-100),
        ]
    )

    def serialize(self):
        return {
            "token": self.token,
            "bias": self.bias,
        }


class OpenAIMessage(Model):
    class Meta:
        verbose_name_plural = "OpenAI Messages"

    def __str__(self):
        return str(self.description)

    description = CharField(
        default="",
        max_length=255,
    )
    content = TextField()
    role = ForeignKey(OpenAIMessageRole, on_delete=PROTECT)
    name = CharField(
        max_length=255,
        default=None,
        null=True,
        blank=True,
    )

    def serialize(self):
        m_dict = {
            "role": self.role.name,
            "content": self.content,
        }
        if self.name is not None:
            m_dict["name"] = self.name

        return m_dict


class OpenAIChat_messages(Model):
    openaichat = ForeignKey("OpenAIChat", on_delete=CASCADE)
    openaimessage = ForeignKey("OpenAIMessage", on_delete=CASCADE)
    order = PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class OpenAIChat(Model):
    class Meta:
        verbose_name_plural = "OpenAI Chat Configuration"

    def __str__(self):
        return self.identifier

    identifier = CharField(
        max_length=255,
        unique=True,
    )
    active = BooleanField(default=True)
    endpoint = CharField(max_length=255)
    api_key = CharField(max_length=255)
    messages = ManyToManyField(OpenAIMessage, through=OpenAIChat_messages)
    model = ForeignKey(OpenAIModel, on_delete=PROTECT)
    stream = BooleanField(default=False)

    frequency_penalty = FloatField(
        default=None,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-2),
            MaxValueValidator(2),
        ],
    )

    logit_bias = ManyToManyField(
        OpenAILogitBias,
        blank=True,
    )

    max_tokens = IntegerField(
        default=None,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2000),
        ],
    )

    presence_penalty = FloatField(
        default=None,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-2),
            MaxValueValidator(2),
        ],
    )

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

    user = CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        # Invalidate ddxtest client if a chat is updated
        if self.pk:
            from api.ddxtest import invalidate_client_cache

            invalidate_client_cache(self.pk)

        super().save(*args, **kwargs)

    def serialize(self):
        result = {
            "pk": self.pk,
            "identifier": self.identifier,
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "model": self.model.name,
            "stream": self.stream,
            "messages": [
                m.serialize()
                for m in self.messages.all().order_by("openaichat_messages__order")
            ],
        }

        logit_bias = self.logit_bias.all()
        if logit_bias:
            result["logit_bias"] = [lb.serialize() for lb in logit_bias]

        for attr in [
            "frequency_penalty",
            "max_tokens",
            "presence_penalty",
            "temperature",
            "top_p",
            "user",
        ]:
            val = getattr(self, attr)
            if val is not None:
                result[attr] = val

        return result


class OpenAIChatCluster(Model):
    class Meta:
        verbose_name_plural = "OpenAI Chat Cluster"

    def __str__(self):
        return str(self.identifier)

    identifier = CharField(max_length=255)
    diagnoses = ForeignKey(
        OpenAIChat,
        on_delete=PROTECT,
        related_name="diagnoses",
    )
    examinations = ForeignKey(
        OpenAIChat,
        on_delete=PROTECT,
        related_name="examinations",
    )
    details = ForeignKey(
        OpenAIChat,
        on_delete=PROTECT,
        related_name="details",
    )

    def serialize(self):
        return {
            "diagnoses": self.diagnoses.serialize(),
            "examinations": self.examinations.serialize(),
            "details": self.details.serialize(),
        }


class Diagnosis(Model):
    class Meta:
        verbose_name_plural = "Diagnoses"

    def __str__(self):
        return self.name

    def serialize(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "pattern": self.pattern,
        }

    name = CharField(max_length=255)
    pattern = CharField(max_length=255)


class DDXTestGroup(Model):
    def __str__(self):
        return str(self.name)

    def serialize(self):
        return {
            "name": self.name,
        }

    name = CharField(max_length=255)


class DDXTestCase(Model):
    def __str__(self):
        return str(self.name)

    def truncated_input(self):
        elipsis = "" if len(self.input) < 100 else "..."
        return str(self.input)[0:100] + elipsis

    def diagnosis_list(self):
        return ", ".join([str(g) for g in self.diagnoses.all()])

    def group_list(self):
        return ", ".join([str(g) for g in self.groups.all()])

    def serialize(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "input": self.input,
            "diagnoses": [d.serialize() for d in self.diagnoses.all()],
            "groups": [g.serialize() for g in self.groups.all()],
        }

    name = CharField(max_length=255)
    input = TextField()
    diagnoses = ManyToManyField(Diagnosis)
    groups = ManyToManyField(DDXTestGroup)


class DDXTestRun(Model):
    def __str__(self):
        return f"Test run: {self.pk}"

    class Status(TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        STARTED = "started", "Started"
        FAILED = "failed", "Failed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    status = CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )

    timestamp = DateTimeField(auto_now_add=True)
    group = ForeignKey(DDXTestGroup, on_delete=PROTECT)
    chat = ForeignKey(OpenAIChat, on_delete=PROTECT)


class DDXCaseResult_diagnoses(Model):
    def __str__(self):
        return str(f"{self.diagnosis}: {self.rank}")

    ddxcaseresult = ForeignKey("DDXCaseResult", on_delete=CASCADE)
    diagnosis = ForeignKey("Diagnosis", on_delete=CASCADE)
    rank = PositiveIntegerField(default=0)

    class Meta:
        ordering = ["rank"]


class DDXCaseResult(Model):
    def __str__(self):
        return str(f"Result: {self.case.name}")

    def chat(self):
        return self.run.chat

    def patterns(self):
        return "\n".join([d.pattern for d in self.case.diagnoses.all()])

    def ranks(self):
        return "\n".join(
            [str(d) for d in DDXCaseResult_diagnoses.objects.filter(ddxcaseresult=self)]
        )

    def timestamp(self):
        return self.run.timestamp

    run = ForeignKey(DDXTestRun, on_delete=CASCADE)
    case = ForeignKey(DDXTestCase, on_delete=PROTECT)
    response = TextField()
    diagnoses = ManyToManyField(Diagnosis, through=DDXCaseResult_diagnoses)


class PromptHistory(Model):
    class Meta:
        verbose_name_plural = "Prompt history"

    def __str__(self):
        return str(self.timestamp)

    config = ForeignKey(OpenAIChat, on_delete=PROTECT)
    user = ForeignKey(User, on_delete=PROTECT)
    prompt = TextField()
    response = TextField()
    timestamp = DateTimeField(auto_now_add=True)


class AIUser(Model):
    def __str__(self):
        return str(self.user.username)

    user = OneToOneField(User, on_delete=PROTECT)
    config = ForeignKey(OpenAIChat, on_delete=PROTECT)
