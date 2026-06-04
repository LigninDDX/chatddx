import json
from functools import cached_property
from typing import final, override

import jsonschema
from pydantic_ai import (
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from chatddx.core.choices import MessageKindChoices, RoleChoices
from chatddx.history.models import MessageModel, SessionModel
from chatddx.history.schemas import MessageSpec
from chatddx.repo.trail_cache import trail_cache
from chatddx.repo.trail_specs import AgentSpec
from chatddx.runtime.utils import get_part_content
from chatddx.utils import truncate_content


class Session(SessionModel):
    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    @override
    def __str__(self):
        if self.description:
            return self.description[:100]
        return f"[{self.uuid}]"

    @cached_property
    def message_count(self):
        return len(self.messages.all())


class Message(MessageModel):
    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    @override
    def __str__(self):
        return f"[{self.role}]: " + truncate_content(self.content, 55)

    @cached_property
    def spec(self):
        return MessageSpec.model_validate(self)

    @cached_property
    def agent_spec(self) -> AgentSpec:
        return trail_cache.get_sync(AgentSpec, self.agent.pk)

    @cached_property
    def output_schema(self):
        return self.agent_spec.output_type.definition

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
    def typed_content(self):
        if self.content is None:
            return None

        if self.output_schema and self.role == RoleChoices.ASSISTANT.value:
            data = json.loads(self.content)
            jsonschema.validate(
                instance=data,
                schema=self.output_schema,
            )
            return data
        else:
            return self.content

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
                        raise NotImplementedError(f"unhandled value '{self.spec.role}'")

            case MessageKindChoices.RESPONSE:
                match self.spec.role:
                    case RoleChoices.ASSISTANT:
                        part_text = get_part_content(
                            self.spec.payload.parts,
                            TextPart,
                        )

                        part_tool_call = truncate_content(
                            get_part_content(
                                self.spec.payload.parts,
                                ToolCallPart,
                            ),
                            20,
                        )

                        if part_text and part_tool_call:
                            raise NotImplementedError(
                                "unhandled combo part with both text and tool call"
                            )

                        if part_tool_call:
                            part_content = f"[tool call]: {part_tool_call}"
                        else:
                            part_content = part_text

                    case _:
                        raise NotImplementedError(f"unhandled value '{self.spec.role}'")

        return part_content
