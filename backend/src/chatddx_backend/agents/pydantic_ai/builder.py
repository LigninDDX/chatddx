# src/chatddx_backend/agents/pydantic_ai.py
from typing import Any, get_args

import jsonschema
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import (
    ModelProfile,
    ModelRetry,
    ModelSettings,
    RunContext,
)
from pydantic_ai import Tool as PydanticTool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import StructuredOutputMode
from pydantic_ai.providers.openai import OpenAIProvider

from chatddx_backend.agents.models.enums import ToolChoices, ValidationChoices
from chatddx_backend.agents.pydantic_ai import tools
from chatddx_backend.agents.pydantic_ai.context import (
    AgentContext,
    OutputType,
    jsonschema_to_type,
)
from chatddx_backend.agents.schemas import AgentSpec, SamplingParamsSpec, ToolGroupSpec


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
    if agent_spec.connection is None:
        raise ValueError("No connection defined for this agent.")

    model_kwargs: dict[str, Any] = {}
    profile_kwargs: dict[str, Any] = {}

    if agent_spec.coercion_strategy == "native":
        profile_kwargs["supports_json_schema_output"] = True

    if agent_spec.coercion_strategy == "prompted":
        profile_kwargs["ignore_streamed_leading_whitespace"] = True

    if agent_spec.coercion_strategy in get_args(StructuredOutputMode):
        profile_kwargs["default_structured_output_mode"] = agent_spec.coercion_strategy
        model_kwargs["profile"] = ModelProfile(**profile_kwargs)

    model_kwargs["model_name"] = agent_spec.connection.model
    model_kwargs["provider"] = OpenAIProvider(base_url=agent_spec.connection.endpoint)

    return OpenAIChatModel(**model_kwargs)


def build_config(sampling_params_spec: SamplingParamsSpec) -> ModelSettings:
    settings_kwargs: dict[str, Any] = {}
    if sampling_params_spec.seed is not None:
        settings_kwargs["seed"] = sampling_params_spec.seed

    if sampling_params_spec.temperature is not None:
        settings_kwargs["temperature"] = sampling_params_spec.temperature

    if sampling_params_spec.provider_params:
        settings_kwargs.update(sampling_params_spec.provider_params)

    return ModelSettings(**settings_kwargs)


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
    """Helper to consistently extract the raw python type from a spec."""
    if agent_spec.output_type:
        return jsonschema_to_type(agent_spec.output_type.definition)
    return str


async def validate_output(
    ctx: RunContext[AgentContext],
    output: OutputType,
) -> OutputType:
    validation_strategy = ctx.deps.agent.validation_strategy
    strategies = ValidationChoices

    if validation_strategy == strategies.NOOP:
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
        match validation_strategy:
            case strategies.INFORM:
                return output | {"__error__": e.message}
            case strategies.RETRY:
                raise ModelRetry(e.message) from e
            case strategies.CRASH:
                raise RuntimeError(f"Validation failed: {e.message}") from e
