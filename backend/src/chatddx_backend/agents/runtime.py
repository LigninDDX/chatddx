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

from chatddx_backend.agents import tools
from chatddx_backend.agents.models import Agent, Tool
from chatddx_backend.agents.types import AgentDeps

OutputType = bool | int | str | float | list | dict[str, Any]


async def validate_output(ctx: RunContext[AgentDeps], output: OutputType) -> OutputType:

    if ctx.partial_output or ctx.deps.schema is None:
        return output

    if not isinstance(output, dict):
        return output

    try:
        jsonschema.validate(instance=output, schema=ctx.deps.schema)
        return output
    except jsonschema.ValidationError as e:
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.RETRY:
            raise ModelRetry(e.message) from e
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.INFORM:
            return output | {"__error__": e.message}
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.CRASH:
            raise RuntimeError(f"Validation failed: {e.message}") from e

    raise RuntimeError(
        f"Unknown validation_strategy: {ctx.deps.validation_strategy!r}. Stale database value?"
    )


def build_model(agent):
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


def build_settings(agent):
    if agent.config is None:
        return None

    settings_kwargs: dict[str, Any] = {}
    if agent.config.seed is not None:
        settings_kwargs["seed"] = agent.config.seed

    if agent.config.temperature is not None:
        settings_kwargs["temperature"] = agent.config.temperature

    if agent.config.provider_params is not None:
        settings_kwargs.update(agent.config.provider_params)

    return ModelSettings(**settings_kwargs)


def build_tools(agent):
    return [
        PydanticTool(
            getattr(tools, tool.name),
            takes_ctx=True,
        )
        for tool in agent.tools.all()
        if tool.type == Tool.ToolType.FUNCTION
    ]


def build_pydantic_agent(agent):

    model = build_model(agent)
    model_settings = build_settings(agent)

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

    pydantic_agent = PydanticAgent(
        model,
        name=agent.name,
        instructions=agent.instructions,
        tools=tools,
        deps_type=AgentDeps,
        output_type=output_type,
        model_settings=model_settings,
    )

    if agent.validation_strategy != Agent.ValidationStrategy.NONE:
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


def run_sync(agent, prompt):
    pa, deps = build_pydantic_agent(agent)
    result = pa.run_sync(prompt, deps=deps)
    return result
