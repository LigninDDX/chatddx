# src/chatddx_backend/agents/type_map.py
from typing import Any, overload

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
    AgentSpec,
    ConnectionSchema,
    ConnectionSpec,
    OutputTypeSchema,
    OutputTypeSpec,
    SamplingParamsSchema,
    SamplingParamsSpec,
    ToolGroupSchema,
    ToolGroupSpec,
    ToolSchema,
    ToolSpec,
)
from chatddx_backend.agents.trail import TrailModel, TrailSchema, TrailSpec

type TypeMap = tuple[type[TrailSpec], type[TrailModel], type[TrailSchema]]


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
