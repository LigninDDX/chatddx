# src/chatddx_backend/agents/type_map.py
from typing import Any, TypeVar, overload

from chatddx_backend.agents.models import (
    Agent,
    Connection,
    OutputType,
    SamplingParams,
    Tool,
    ToolGroup,
)
from chatddx_backend.agents.schemas import (
    AgentSchema,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolSchema,
)
from chatddx_backend.agents.specs import (
    AgentSpec,
    ConnectionSpec,
    OutputTypeSpec,
    SamplingParamsSpec,
    ToolGroupSpec,
    ToolSpec,
)
from chatddx_backend.agents.trail import TrailModel, TrailSchema, TrailSpec

type TypeMap = tuple[type[TrailSpec], type[TrailModel], type[TrailSchema]]

T = TypeVar("T", TrailSchema, TrailModel, TrailSpec)

type_maps: list[TypeMap] = [
    (ConnectionSpec, Connection, ConnectionSchema),
    (SamplingParamsSpec, SamplingParams, SamplingParamsSchema),
    (ToolGroupSpec, ToolGroup, ToolGroupSchema),
    (ToolSpec, Tool, ToolSchema),
    (OutputTypeSpec, OutputType, OutputTypeSchema),
    (AgentSpec, Agent, AgentSchema),
]


@overload
def resolve(source: Any, target: type[TrailSpec]) -> type[TrailSpec]: ...


@overload
def resolve(source: Any, target: type[TrailModel]) -> type[TrailModel]: ...


@overload
def resolve(source: Any, target: type[TrailSchema]) -> type[TrailSchema]: ...


def resolve(source: Any, target: Any) -> Any:
    bases = (TrailSpec, TrailModel, TrailSchema)
    target_col = next(i for i, base in enumerate(bases) if issubclass(target, base))
    source_col = next(i for i, base in enumerate(bases) if issubclass(source, base))

    for row in type_maps:
        if row[source_col] is source:
            return row[target_col]

    raise KeyError(f"No type map entry found for {source}")
