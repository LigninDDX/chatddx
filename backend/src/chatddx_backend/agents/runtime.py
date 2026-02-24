from dataclasses import dataclass
from typing import Any

import jsonschema
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import (
    ModelProfile,
    ModelRetry,
    ModelSettings,
    RunContext,
    StructuredDict,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from chatddx_backend.agents.models import Agent


def filter_none(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


@dataclass
class AgentResult:
    output: dict[str, Any]
    validation_error: str | None = None


@dataclass(frozen=True)
class AgentDeps:
    output_type: dict[str, Any] | None
    validation_strategy: Agent.ValidationStrategy


@dataclass
class StreamChunk:
    text: str


@dataclass
class StreamComplete:
    output: dict


@dataclass
class StreamValidationError:
    output: dict
    error: str


StreamEvent = StreamChunk | StreamComplete | StreamValidationError


class ValidationInformError(Exception):
    def __init__(self, message: str, output: dict[str, Any]):
        super().__init__(message)
        self.output = output


async def validate_output(
    ctx: RunContext[AgentDeps], output: dict[str, Any]
) -> dict[str, Any]:

    if ctx.deps.output_type is None or ctx.partial_output:
        return output

    try:
        jsonschema.validate(instance=output, schema=ctx.deps.output_type)
        return output
    except jsonschema.ValidationError as e:
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.RETRY:
            raise ModelRetry(e.message) from e
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.INFORM:
            raise ValidationInformError(e.message, output) from e
        if ctx.deps.validation_strategy == Agent.ValidationStrategy.CRASH:
            raise RuntimeError(f"Validation failed: {e.message}") from e

    raise RuntimeError(
        f"Unknown validation_strategy: {ctx.deps.validation_strategy!r}. Stale database value?"
    )


def build_pydantic_agent(agent):
    if agent.connection is None:
        raise ValueError("No connection defined for this agent.")
    if agent.config is None:
        raise ValueError("No config defined for this agent.")
    if agent.output_type is None:
        raise ValueError("No output type defined for this agent.")

    pa = PydanticAgent(
        OpenAIChatModel(
            model_name=agent.connection.model,
            provider=OpenAIProvider(base_url=agent.connection.endpoint),
            # profile=ModelProfile(
            #     default_structured_output_mode="prompted",
            #     ignore_streamed_leading_whitespace=True,
            # ),
        ),
        name=agent.name,
        instructions=agent.instructions,
        deps_type=AgentDeps,
        output_type=StructuredDict(agent.output_type),
        model_settings=ModelSettings(
            **filter_none(
                seed=agent.config.seed,
                temperature=agent.config.temperature,
            )
        ),
    )
    pa.output_validator(validate_output)

    return pa


def build_prompt_deps(agent):
    return AgentDeps(
        output_type=agent.output_type,
        validation_strategy=Agent.ValidationStrategy(agent.validation_strategy),
    )


async def run_stream(agent: Agent, prompt: str):
    pa: PydanticAgent[AgentDeps, dict[str, Any]] = build_pydantic_agent(agent)
    deps: AgentDeps = build_prompt_deps(agent)

    async with pa.run_stream(prompt, deps=deps) as result:
        async for chunk in result.stream_output(debounce_by=0.1):
            yield chunk


async def run_async(agent: Agent, prompt: str) -> AgentResult:
    pa = build_pydantic_agent(agent)
    deps = build_prompt_deps(agent)

    try:
        r = await pa.run(prompt, deps=deps)
    except ValidationInformError as e:
        result = AgentResult(output=e.output, validation_error=str(e))
    else:
        result = AgentResult(output=r.output)

    return result


def run_sync(agent, prompt):
    pa = build_pydantic_agent(agent)
    deps = build_prompt_deps(agent)

    try:
        r = pa.run_sync(prompt, deps=deps)
    except ValidationInformError as e:
        result = AgentResult(output=e.output, validation_error=str(e))
    else:
        result = AgentResult(output=r.output)

    return result
