from typing import Any, Sequence, get_args

import jsonschema
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import (
    ModelMessage,
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

from chatddx_backend.agents import tools
from chatddx_backend.agents.models import Agent, SamplingParams, Tool
from chatddx_backend.agents.types import AgentDeps

OutputType = bool | int | str | float | list[Any] | dict[str, Any]


async def validate_output(ctx: RunContext[AgentDeps], output: OutputType) -> OutputType:
    validation_strategy = ctx.deps.validation_strategy
    strategies = Agent.ValidationStrategy

    if validation_strategy == strategies.NOOP:
        return output

    if ctx.partial_output or ctx.deps.schema is None:
        return output

    if not isinstance(output, dict):
        return output

    try:
        jsonschema.validate(instance=output, schema=ctx.deps.schema)
        return output
    except jsonschema.ValidationError as e:
        match validation_strategy:
            case strategies.INFORM:
                return output | {"__error__": e.message}
            case strategies.RETRY:
                raise ModelRetry(e.message) from e
            case strategies.CRASH:
                raise RuntimeError(f"Validation failed: {e.message}") from e


def build_model(agent: Agent):
    if agent.connection is None:
        raise ValueError("No connection defined for this agent.")

    model_kwargs: dict[str, Any] = {}
    profile_kwargs: dict[str, Any] = {}

    if agent.coercion_strategy == "native":
        profile_kwargs["supports_json_schema_output"] = True

    if agent.coercion_strategy == "prompted":
        profile_kwargs["ignore_streamed_leading_whitespace"] = True

    if agent.coercion_strategy in get_args(StructuredOutputMode):
        profile_kwargs["default_structured_output_mode"] = agent.coercion_strategy
        model_kwargs["profile"] = ModelProfile(**profile_kwargs)

    model_kwargs["model_name"] = agent.connection.model
    model_kwargs["provider"] = OpenAIProvider(base_url=agent.connection.endpoint)

    return OpenAIChatModel(**model_kwargs)


def build_config(sampling_params: SamplingParams):
    settings_kwargs: dict[str, Any] = {}
    if sampling_params.seed is not None:
        settings_kwargs["seed"] = sampling_params.seed

    if sampling_params.temperature is not None:
        settings_kwargs["temperature"] = sampling_params.temperature

    if sampling_params.provider_params:
        settings_kwargs.update(sampling_params.provider_params)

    return ModelSettings(**settings_kwargs)


def build_tools(agent: Agent):
    return [
        PydanticTool(
            getattr(tools, tool.name),
            takes_ctx=True,
        )
        for tool in agent.tools.all()
        if tool.type == Tool.ToolType.FUNCTION.value
    ]


def build_pydantic_agent(
    agent: Agent,
) -> tuple[PydanticAgent[AgentDeps, OutputType], AgentDeps]:

    model = build_model(agent)

    model_settings = (
        build_config(agent.sampling_params) if agent.sampling_params else None
    )

    tools = []
    if agent.use_tools:
        tools = build_tools(agent)

    if agent.schema is None:
        output_type = str
        schema = None
    else:
        schema = agent.schema.definition
        match agent.schema.definition.get("type"):
            case "bool":
                output_type = bool
            case "integer":
                output_type = int
            case "number":
                output_type = float
            case "array":
                output_type = list
            case "object":
                output_type = StructuredDict(agent.schema.definition)
            case _:
                invalid_type = agent.schema.definition.get("type")
                raise ValueError(f"Unexpected schema type '{invalid_type}'")

    pydantic_agent = PydanticAgent[AgentDeps, OutputType](
        model,
        name=agent.name,
        instructions=agent.instructions,
        tools=tools,
        deps_type=AgentDeps,
        output_type=output_type,
        model_settings=model_settings,
    )

    pydantic_agent.output_validator(validate_output)

    agent_deps = AgentDeps(
        schema=schema,
        validation_strategy=Agent.ValidationStrategy(agent.validation_strategy),
    )

    return pydantic_agent, agent_deps


async def run_stream(agent: Agent, prompt: str):
    pa, deps = build_pydantic_agent(agent)

    async with pa.run_stream(prompt, deps=deps) as result:
        async for chunk in result.stream_output(debounce_by=0.1):
            yield chunk


async def run_async(agent: Agent, prompt: str):
    pa, deps = build_pydantic_agent(agent)
    result = await pa.run(
        prompt,
        deps=deps,
    )
    return result


def run_sync(
    agent: Agent,
    prompt: str,
    history: Sequence[ModelMessage],
):
    pa, deps = build_pydantic_agent(agent)
    result = pa.run_sync(
        prompt,
        deps=deps,
        message_history=history,
    )
    return result
