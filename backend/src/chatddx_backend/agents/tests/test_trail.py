# src/chatddx_backend/agents/tests/test_trail.py
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, Type, TypeAlias

import pytest
from django.contrib.postgres.fields.array import ArrayField

from chatddx_backend.agents.managers import TrailManager
from chatddx_backend.agents.models import (
    Agent,
    Connection,
    RelatedArrayField,
    SamplingParams,
    Schema,
    Tool,
    ToolGroup,
    TrailModel,
)


@pytest.fixture
def trail_manager():
    return TrailManager(
        library={
            "connection": {
                "connection-1": {
                    "model": "Test/test-base",
                    "provider": "vllm",
                    "endpoint": "http://example.com/v1/",
                },
            },
            "schema": {
                "schema-1": {
                    "definition": {
                        "type": "object",
                        "properties": {
                            "type": "object",
                            "properties": {
                                "integer": {"type": "integer"},
                                "list": {"items": {"type": "string"}, "type": "array"},
                                "bool": {"type": "boolean"},
                            },
                            "required": ["integer", "list", "bool"],
                        },
                    },
                }
            },
            "sampling_params": {
                "sampling_params-1": {
                    "temperature": 0.7,
                    "max_tokens": 150,
                    "stop_sequences": ["\\n\\n", "END"],
                }
            },
            "tool": {
                "tool-1": {
                    "type": "function",
                    "description": "Complex parameters",
                    "parameters": {
                        "bool": True,
                        "float": 3.1415,
                        "dict": {"key": "value"},
                        "list": [1, 2],
                    },
                },
                "tool-1 ": {
                    "type": "function",
                    "description": "Trailing space",
                    "parameters": {
                        "bool": False,
                    },
                },
            },
            "tool_group": {
                "tool_group-1": {
                    "instructions": "use these tools",
                    "tools": [
                        "tool-1",
                    ],
                },
            },
            "agent": {
                "agent-1": {
                    "instructions": "hello",
                    "sampling_params": "sampling_params-1",
                    "connection": "connection-1",
                    "schema": "schema-1",
                    "tool_group": "tool_group-1",
                }
            },
        }
    )


JSONLike: TypeAlias = (
    str
    | int
    | float
    | Decimal
    | datetime
    | list["JSONLike"]
    | dict[str, "JSONLike"]
    | TrailModel
)

RelatedRepresentation = Literal["pk", "name", None]


def make_tiny_change(value: JSONLike) -> JSONLike:
    match value:
        case str():
            return value + " "
        case bool():
            return not value
        case int():
            return value + 1
        case float():
            return value + 0.1
        case Decimal():
            return value + Decimal("0.1")
        case dict():
            if value:
                some_key = next(iter(value))
                return value | {some_key: make_tiny_change(value[some_key])}
            else:
                return {"": ""}
        case list():
            return [make_tiny_change(value[0])] + value[1:] if value else [""]
        case TrailModel():
            value.pk = None
            value.name += "."
            return value

        case _:
            raise TypeError(f"type '{type(value)}' not supported")


def serialize(
    instance: TrailModel,
    related_representation: RelatedRepresentation,
) -> dict[str, Any]:

    data: dict[str, Any] = {}

    for field in instance._meta.concrete_fields:
        if field.primary_key:
            continue

        data[field.name] = serialize_field(instance, field.name, related_representation)

    return data


def serialize_field(
    instance: TrailModel,
    field_name: str,
    related_representation: RelatedRepresentation,
) -> Any:
    field = instance._meta.get_field(field_name)
    value = getattr(instance, field.name)

    if isinstance(field, RelatedArrayField):
        if related_representation == "pk":
            return value

        instances = [field.related_model.objects.get(pk=item) for item in value]

        if related_representation is None:
            return instances

        return [getattr(i, related_representation) for i in instances]

    if value is None or related_representation is None:
        return value

    if isinstance(value, TrailModel):
        return getattr(value, related_representation)

    return value


def deeptouch(value: JSONLike) -> JSONLike:
    match value:
        case str():
            return value + ""
        case bool():
            return bool(value)
        case int():
            return value + 0
        case float():
            return value + 0
        case Decimal():
            return value + Decimal("0.0")
        case dict():
            return {k: deeptouch(v) for k, v in value.items()}
        case list():
            return [deeptouch(v) for v in value]
        case datetime():
            return value
        case TrailModel():
            return value
        case _:
            raise TypeError(f"type '{type(value)}' not supported")


def get_library_value(
    trail_manager: TrailManager,
    Model: Type[TrailModel],
    record: str,
    field: dict[str, Any],
):
    (field_name,) = field.keys()
    value = trail_manager.library[Model.record_name()][record][field_name]

    match field[field_name]:
        case Decimal():
            return Decimal(str(value))
        case _:
            return value


fields = [
    (Connection, "model"),
    (Connection, "endpoint"),
    (Connection, "provider"),
    (SamplingParams, "temperature"),
    (SamplingParams, "stop_sequences"),
    (Tool, "parameters"),
    (ToolGroup, "instructions"),
    (ToolGroup, "tools"),
    (Schema, "definition"),
    (Agent, "instructions"),
    (Agent, "connection"),
    (Agent, "schema"),
    (Agent, "sampling_params"),
    (Agent, "tool_group"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("Model, field_name", fields)
@pytest.mark.parametrize("library_set", [(1)])
class TestTrail:
    @pytest.mark.parametrize("related_representation", [(None), ("name")])
    def test_upsert_identical(
        self,
        trail_manager: TrailManager,
        Model: Type[TrailModel],
        field_name: str,
        library_set: int,
        related_representation: RelatedRepresentation,
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)

        field = {
            field_name: serialize_field(
                instance0,
                field_name,
                related_representation,
            )
        }

        instance1 = trail_manager.get_instance(
            Model,
            record,
            **serialize(instance0, related_representation) | field,
        )

        if isinstance(instance0._meta.get_field(field_name), RelatedArrayField):
            if related_representation is None:
                field[field_name] = [item.name for item in field[field_name]]

        value = getattr(field[field_name], "name", field[field_name])

        assert value == get_library_value(
            trail_manager,
            Model,
            record,
            field,
        )

        assert instance0.name == instance1.name
        assert instance0.fingerprint == instance1.fingerprint

        assert instance0.created_at == instance0.updated_at == instance1.created_at
        assert instance1.updated_at > instance1.created_at

    @pytest.mark.parametrize("related_representation", [(None), ("name"), ("pk")])
    def test_upsert_identical_touched(
        self,
        trail_manager: TrailManager,
        Model: Type[TrailModel],
        field_name: str,
        library_set: int,
        related_representation: RelatedRepresentation,
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)

        field = {
            field_name: deeptouch(
                serialize_field(
                    instance0,
                    field_name,
                    related_representation,
                )
            )
        }

        instance1 = trail_manager.get_instance(
            Model,
            record,
            **serialize(instance0, related_representation) | field,
        )

        assert getattr(instance0, field_name) == getattr(instance1, field_name)

        assert instance0.name == instance1.name
        assert instance0.fingerprint == instance1.fingerprint

        assert instance0.created_at == instance0.updated_at == instance1.created_at
        assert instance1.updated_at > instance1.created_at

    @pytest.mark.parametrize("related_representation", [(None), ("name"), ("pk")])
    def test_upsert_variation(
        self,
        trail_manager: TrailManager,
        Model: Type[TrailModel],
        field_name: str,
        library_set: int,
        related_representation: RelatedRepresentation,
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)

        if instance0._meta.get_field(field_name).many_to_one:
            pytest.skip(
                f"Mutation testing not supported for many_to_one field: {field_name}"
            )

        field = {
            field_name: make_tiny_change(
                serialize_field(
                    instance0,
                    field_name,
                    related_representation,
                )
            )
        }

        instance1 = trail_manager.get_instance(
            Model,
            record,
            **serialize(instance0, related_representation) | field,
        )

        assert getattr(instance0, field_name) != getattr(instance1, field_name)

        assert instance0.name == instance1.name
        assert instance0.fingerprint != instance1.fingerprint

        assert instance0.created_at == instance0.updated_at
        assert instance1.created_at == instance1.updated_at
