# src/chatddx_backend/agents/state.py
from typing import Any, TypeVar, cast

from chatddx_backend.agents.models import Agent, TrailModel
from chatddx_backend.agents.registry import data_from_registry
from chatddx_backend.agents.schema import AgentSpec, TrailSchema, TrailSpec
from chatddx_backend.agents.utils import (
    ListField,
    SingleField,
    value_is_or_list_of,
)

T = TypeVar("T", bound=TrailSchema)
S = TypeVar("S", bound=TrailModel)


def agent_spec_from_registry(
    name: str,
    registry: dict[str, Any],
) -> AgentSpec:
    return cast(AgentSpec, spec_from_registry(Agent, name, registry))


def agent_spec_from_data(
    data: dict[str, Any],
) -> AgentSpec:
    return cast(AgentSpec, spec_from_data(Agent, data))


def spec_from_registry(
    Model: type[TrailModel],
    name: str,
    registry: dict[str, Any],
) -> TrailSpec:
    data = data_from_registry(Model.Schema, name, registry)
    return spec_from_data(Model, data)


def spec_from_data(
    Model: type[TrailModel],
    data: dict[str, Any],
) -> TrailSpec:
    model = model_from_data(Model, data)
    return Model.Spec.model_validate(model)


def spec_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
) -> TrailSpec:
    model = model_from_schema(Model, schema)
    return Model.Spec.model_validate(model)


def model_from_data(
    Model: type[TrailModel],
    data: dict[str, Any],
) -> TrailModel:
    schema = schema_from_data(Model.Schema, data)
    return model_from_schema(Model, schema)


def model_from_schema(
    Model: type[TrailModel],
    schema: TrailSchema,
) -> TrailModel:
    values = {}

    for key, value in schema:
        field = Model._meta.get_field(key)
        related_model = getattr(field, "related_model", None)

        match value_is_or_list_of(TrailSchema, value):
            case SingleField() if related_model:
                values[key] = model_from_schema(related_model, value)
            case ListField() if related_model:
                values[key] = [model_from_schema(related_model, v) for v in value]
            case None:
                values[key] = value
            case _:
                raise ValueError(f"'{value}' is a relation but lacks related_model")

    return Model.apply(**values)


def schema_from_registry(
    Schema: type[T],
    name: str,
    registry: dict[str, Any],
) -> T:
    data = data_from_registry(Schema, name, registry)
    return schema_from_data(Schema, data)


def schema_from_data(
    Schema: type[T],
    data: dict[str, Any],
) -> T:
    return Schema.model_validate(data)


def schema_from_spec(
    Schema: type[T],
    spec: TrailSpec,
) -> T:
    return Schema.model_validate(spec.model_dump())
