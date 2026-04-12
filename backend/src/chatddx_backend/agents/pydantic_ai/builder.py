# src/chatddx_backend/agents/pydantic_ai.py
from decimal import Decimal
from typing import Any, get_args

import jsonschema
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import (
    ModelProfile,
    ModelRetry,
    ModelSettings,
    RunContext,
    StructuredDict,
)
from pydantic_ai import Tool as PydanticTool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import StructuredOutputMode
from pydantic_ai.providers.openai import OpenAIProvider

from chatddx_backend.agents.models.choices import ToolChoices, ValidationChoices
from chatddx_backend.agents.pydantic_ai import tools
from chatddx_backend.agents.pydantic_ai.context import (
    AgentContext,
    OutputType,
)
from chatddx_backend.agents.schemas import (
    AgentSpec,
    SamplingParamsSchema,
    SamplingParamsSpec,
    ToolGroupSpec,
)
from chatddx_backend.agents.trail import schema_from_spec


def build_agent(
    agent_spec: AgentSpec,
    output_type: type[OutputType],
) -> PydanticAgent[AgentContext, OutputType]:

    tools: list[PydanticTool] = []
    model_settings: ModelSettings | None = None

    model: OpenAIChatModel = build_model(agent_spec)

    instructions: str = agent_spec.instructions

    if agent_spec.sampling_params:
        model_settings = build_config(agent_spec.sampling_params)

    if agent_spec.tool_group:
        tools_instructions, tools = build_tools(agent_spec.tool_group)
        if tools_instructions:
            instructions = "\n---\n".join([instructions, tools_instructions])

    pydantic_agent = PydanticAgent[AgentContext, OutputType](
        model,
        name=agent_spec.name,
        instructions=instructions,
        tools=tools,
        deps_type=AgentContext,
        output_type=output_type,
        model_settings=model_settings,
    )

    pydantic_agent.output_validator(validate_output)

    return pydantic_agent


def build_model(agent_spec: AgentSpec):
    model_kwargs: dict[str, Any] = {}
    profile_kwargs: dict[str, Any] = agent_spec.connection.profile.copy()

    if agent_spec.output_type.coercion_strategy in get_args(StructuredOutputMode):
        profile_kwargs["default_structured_output_mode"] = (
            agent_spec.output_type.coercion_strategy
        )

    model_kwargs["profile"] = ModelProfile(**profile_kwargs)
    model_kwargs["model_name"] = agent_spec.connection.model

    model_kwargs["provider"] = OpenAIProvider(
        base_url=str(agent_spec.connection.endpoint)
    )

    return OpenAIChatModel(**model_kwargs)


def build_config(sampling_params_spec: SamplingParamsSpec) -> ModelSettings:
    settings = schema_from_spec(SamplingParamsSchema, sampling_params_spec).model_dump(
        exclude_none=True
    )
    provider_params = settings.pop("provider_params")

    return ModelSettings(settings | provider_params)


def build_tools(
    tool_group_spec: ToolGroupSpec,
) -> tuple[str, list[PydanticTool]]:
    return tool_group_spec.instructions, [
        PydanticTool(
            getattr(tools, tool_spec.name),
            takes_ctx=True,
        )
        for tool_spec in tool_group_spec.tools
        if tool_spec.type == ToolChoices.FUNCTION
    ]


def build_output_type(agent_spec: AgentSpec) -> type[OutputType]:
    schema = agent_spec.output_type.definition
    match schema.get("type"):
        case "bool":
            return bool
        case "integer":
            return int
        case "number":
            return Decimal
        case "array":
            return list
        case "object":
            return StructuredDict(schema)
        case None:
            return str
        case _ as invalid_type:
            raise ValueError(f"Unexpected output type '{invalid_type}'")


async def validate_output(
    ctx: RunContext[AgentContext],
    output: OutputType,
) -> OutputType:
    strategy = ctx.deps.agent.output_type.validation_strategy

    if strategy == ValidationChoices.NOOP:
        return output

    if ctx.partial_output:
        return output

    if not (isinstance(output, dict) and ctx.deps.agent.output_type):
        return output

    try:
        jsonschema.validate(
            instance=output, schema=ctx.deps.agent.output_type.definition
        )
        return output
    except jsonschema.ValidationError as e:
        match strategy:
            case ValidationChoices.INFORM:
                return output | {"__error__": e.message}
            case ValidationChoices.RETRY:
                raise ModelRetry(e.message) from e
            case ValidationChoices.CRASH:
                raise RuntimeError(f"Validation failed: {e.message}") from e
