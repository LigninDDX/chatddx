from functools import cached_property

from django.utils.safestring import mark_safe
from markdown import markdown
from pydantic_ai import (
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from unfold import admin

from chatddx_backend.agents.admin.utils import truncate_content
from chatddx_backend.agents.models import IdentityModel, MessageModel, SessionModel
from chatddx_backend.agents.models.choices import (
    MessageKindChoices,
    RoleChoices,
)
from chatddx_backend.agents.pydantic_ai.utils import get_part_content
from chatddx_backend.agents.schemas import (
    AgentSpec,
    IdentitySpec,
    MessageSpec,
    SessionSpec,
)
from chatddx_backend.agents.trail.cache import trail_cache


class Identity(IdentityModel):
    Spec = IdentitySpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Identity"
        verbose_name_plural = "Identities"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)


class Session(SessionModel):
    Spec = SessionSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    def __str__(self):
        if self.description:
            return self.description[:100]
        return f"[{self.uuid}]"

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)

    @cached_property
    def message_count(self):
        return len(self.messages.all())


class Message(MessageModel):
    Spec = MessageSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"[{self.role}]: " + truncate_content(self.content, 20)

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)

    @cached_property
    def agent_spec(self):
        return trail_cache.get_sync(AgentSpec, self.spec.agent_id)

    @cached_property
    def markdown(self):
        html = markdown(self.content)
        return mark_safe(html)

    @cached_property
    def direction(self):
        return {
            MessageKindChoices.REQUEST: "->",
            MessageKindChoices.RESPONSE: "<-",
        }[self.spec.kind]

    @cached_property
    def parts(self):
        return len(self.spec.payload.parts)

    @cached_property
    def thinking(self):
        part_content = get_part_content(self.spec.payload.parts, ThinkingPart)
        return part_content

    @cached_property
    def content(self):
        match self.spec.kind:
            case MessageKindChoices.REQUEST:
                match self.spec.role:
                    case RoleChoices.USER:
                        part_content = get_part_content(
                            self.spec.payload.parts,
                            UserPromptPart,
                        )
                    case RoleChoices.TOOL:
                        part_content = "[tool return]: " + truncate_content(
                            get_part_content(
                                self.spec.payload.parts,
                                ToolReturnPart,
                            ),
                            20,
                        )
                    case _:
                        raise ValueError(f"unhandled value {self.spec.role}")

            case MessageKindChoices.RESPONSE:
                match self.spec.role:
                    case RoleChoices.ASSISTANT:
                        part_content = get_part_content(
                            self.spec.payload.parts,
                            TextPart,
                        )
                        part_content += " [tool call]: " + truncate_content(
                            get_part_content(
                                self.spec.payload.parts,
                                ToolCallPart,
                            ),
                            20,
                        )
                    case _:
                        raise ValueError(f"unhandled value {self.spec.role}")

        return part_content
