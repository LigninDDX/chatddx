import json
from functools import cached_property

import jsonschema
from pydantic_ai import (
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from chatddx_backend.agents import type_map
from chatddx_backend.agents.admin.utils import truncate_content
from chatddx_backend.agents.models import (
    AgentModel,
    ConnectionModel,
    IdentityModel,
    MessageModel,
    OutputTypeModel,
    SamplingParamsModel,
    SessionModel,
    ToolGroupModel,
)
from chatddx_backend.agents.models.choices import (
    MessageKindChoices,
    RoleChoices,
)
from chatddx_backend.agents.pydantic_ai.utils import get_part_content
from chatddx_backend.agents.schemas import AgentSpec, MessageSpec
from chatddx_backend.agents.trail import TrailSpec
from chatddx_backend.agents.trail.cache import trail_cache


class TrailProxy:
    def __str__(self):
        return ", ".join(getattr(self, "name").split("|"))

    @cached_property
    def spec(self):
        return type_map.resolve(self, TrailSpec).model_validate(self)


class Agent(TrailProxy, AgentModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Agent"
        verbose_name_plural = "Agents"


class Connection(TrailProxy, ConnectionModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Connection"
        verbose_name_plural = "Connections"


class OutputType(TrailProxy, OutputTypeModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Output type"
        verbose_name_plural = "Output types"


class SamplingParams(TrailProxy, SamplingParamsModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Sampling parameters"
        verbose_name_plural = "Sampling parameters"


class ToolGroup(TrailProxy, ToolGroupModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Tool group"
        verbose_name_plural = "Tool groups"


class Identity(IdentityModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Identity"
        verbose_name_plural = "Identities"

    def __str__(self):
        return self.name


class Session(SessionModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    def __str__(self):
        if self.description:
            return self.description[:100]
        return f"[{self.uuid}]"

    @cached_property
    def message_count(self):
        return len(self.messages.all())


class Message(MessageModel):
    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"[{self.role}]: " + truncate_content(self.content, 55)

    @cached_property
    def spec(self):
        return MessageSpec.model_validate(self)

    @cached_property
    def agent_spec(self):
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
                                f"unhandled combo part with both text and tool call"
                            )

                        if part_tool_call:
                            part_content = f"[tool call]: {part_tool_call}"
                        else:
                            part_content = part_text

                    case _:
                        raise NotImplementedError(f"unhandled value '{self.spec.role}'")

        return part_content
