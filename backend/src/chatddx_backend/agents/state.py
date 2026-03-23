# src/chatddx_backend/agents/state.py
from typing import Any, TypeVar

from chatddx_backend.agents.models import Agent, TrailModel
from chatddx_backend.agents.registry import parse_registry
from chatddx_backend.agents.schema import AgentSchema, AgentSpec, TrailSchema, TrailSpec
from chatddx_backend.agents.utils import (
    ListField,
    SingleField,
    value_is_or_list_of,
)

SchemaT = TypeVar("SchemaT", bound=TrailSchema)
SpecT = TypeVar("SpecT", bound=TrailSpec)
ModelT = TypeVar("ModelT", bound=TrailModel)


# Composed convenience functions


def agent_spec_from_registry(
    name: str,
    registry: dict[str, Any],
) -> AgentSpec:
    return spec_from_registry(Agent, AgentSpec, name, registry)


def agent_data_from_registry(
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    return data_from_registry(AgentSchema, name, registry)


def agent_spec_from_data(
    data: dict[str, Any],
) -> AgentSpec:
    return spec_from_data(Agent, AgentSpec, data)


def spec_from_registry(
    Model: type[TrailModel],
    Spec: type[SpecT],
    name: str,
    registry: dict[str, Any],
) -> SpecT:
    data = data_from_registry(Model.Schema, name, registry)
    return spec_from_data(Model, Spec, data)


def spec_from_data(
    Model: type[TrailModel],
    Spec: type[SpecT],
    data: dict[str, Any],
) -> SpecT:
    model = model_from_data(Model, data)
    return Spec.model_validate(model)


def spec_from_schema(
    Model: type[TrailModel],
    Spec: type[SpecT],
    schema: TrailSchema,
) -> SpecT:
    model = model_from_schema(Model, schema)
    return Spec.model_validate(model)


def model_from_data(
    Model: type[ModelT],
    data: dict[str, Any],
) -> ModelT:
    schema = schema_from_data(Model.Schema, data)
    return model_from_schema(Model, schema)


def schema_from_registry(
    Schema: type[SchemaT],
    name: str,
    registry: dict[str, Any],
) -> SchemaT:
    data = data_from_registry(Schema, name, registry)
    return schema_from_data(Schema, data)


# Atomic pipeline steps


def data_from_registry(
    Schema: type[TrailSchema],
    name: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    return parse_registry(Schema, name, registry)


def schema_from_data(
    Schema: type[SchemaT],
    data: dict[str, Any],
) -> SchemaT:
    return Schema.model_validate(data)


def model_from_schema(
    Model: type[ModelT],
    schema: TrailSchema,
) -> ModelT:
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


def spec_from_model(
    Spec: type[SpecT],
    model: TrailModel,
) -> SpecT:
    return Spec.model_validate(model)


def schema_from_spec(
    Schema: type[SchemaT],
    spec: TrailSpec,
) -> SchemaT:
    return Schema.model_validate(spec.model_dump())
