# src/chatddx_backend/agents/tests/test_trail.py
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TypeVar, cast

import pytest
from deepdiff import DeepDiff
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction

from chatddx_backend.agents.models import (
    Agent,
    Connection,
    RelatedArrayField,
    SamplingParams,
    Schema,
    Tool,
    ToolGroup,
    TrailManager,
    TrailModel,
    TrailRelation,
    serialize,
    serialize_field,
)


@pytest.fixture
def trail_manager():
    return TrailManager(
        library={
            "connection": {
                "connection-1": {
                    "model": "Test/test-1",
                    "provider": "vllm",
                    "endpoint": "http://example.com/v1/",
                },
                "connection-1'": {
                    "model": "Test/test-1-prime",
                    "provider": "vllm",
                    "endpoint": "http://example.com/v1'/",
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
                },
                "schema-1'": {
                    "definition": {
                        "type": "object",
                        "properties": {
                            "type": "object",
                            "properties": {
                                "integer": {"type": "integer"},
                                "list": {"items": {"type": "string"}, "type": "array"},
                                "bool": {"type": "boolean"},
                            },
                            "required": ["integer", "list", "int"],
                        },
                    },
                },
            },
            "sampling_params": {
                "sampling_params-1": {
                    "temperature": 0.7,
                    "max_tokens": 150,
                    "stop_sequences": ["\\n\\n", "END"],
                },
                "sampling_params-1'": {
                    "temperature": 0.6,
                    "max_tokens": 100,
                    "stop_sequences": [],
                },
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
                "tool-1'": {
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
                "tool_group-1'": {
                    "instructions": "use these tools prime",
                    "tools": [
                        "tool-1'",
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


JSONLike = (
    str
    | int
    | float
    | Decimal
    | datetime
    | list["JSONLike"]
    | dict[str, "JSONLike"]
    | TrailModel
)
T = TypeVar("T", bound=JSONLike)


def make_tiny_change(value: T) -> T:
    match value:
        case str():
            return cast(T, value + "'")
        case bool():
            return cast(T, not value)
        case int():
            return cast(T, value + 1)
        case float():
            return cast(T, value + 0.1)
        case Decimal():
            return cast(T, value + Decimal("0.1"))
        case datetime():
            return value + timedelta(1)
        case dict():
            if value:
                some_key, some_value = next(iter(value.items()))
                return cast(T, value | {some_key: make_tiny_change(some_value)})
            else:
                return value
        case list():
            return cast(T, [make_tiny_change(value[0])] + value[1:] if value else [])
        case TrailModel():
            value.pk = None
            value.name += "'"
            return value


fields = [
    (Connection, "model"),
    (Connection, "endpoint"),
    (Connection, "provider"),
    (SamplingParams, "temperature"),
    (SamplingParams, "stop_sequences"),
    (Tool, "description"),
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
    @pytest.mark.parametrize("target_type", [(int), (str), (dict), (TrailModel)])
    def test_upsert_identical(
        self,
        trail_manager: TrailManager,
        Model: type[TrailModel],
        field_name: str,
        library_set: int,
        target_type: type[TrailRelation],
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)
        field = instance0._meta.get_field(field_name)

        value = serialize_field(
            instance0,
            field,
            target_type,
        )

        library_value = trail_manager.deref(Model, record)[field.name]

        instance1 = trail_manager.get_instance(
            Model,
            record,
            **serialize(instance0, target_type) | {field.name: value},
        )

        if isinstance(field, RelatedArrayField):
            assert isinstance(value[0], target_type)
            match value[0]:
                case dict() | TrailModel():
                    if isinstance(value[0], TrailModel):
                        value = [serialize(v, dict) for v in value]

                    diff = DeepDiff(
                        value,
                        library_value,
                        ignore_order=True,
                        ignore_numeric_type_changes=True,
                        exclude_regex_paths=[
                            r".*\['(id|fingerprint|created_at|updated_at)'\]"
                        ],
                    )
                    assert not diff
                case str():
                    assert value == [v["name"] for v in library_value]
                case _:
                    pytest.skip(f"not testing {type(value[0])}")

        elif field.many_to_one or field.one_to_one:
            assert isinstance(value, target_type)
            match value:
                case dict() | TrailModel():
                    if isinstance(value, TrailModel):
                        value = serialize(value, dict)

                    diff = DeepDiff(
                        value,
                        library_value,
                        ignore_numeric_type_changes=True,
                        exclude_obj_callback=lambda o, p: not o,
                        exclude_regex_paths=[
                            r".*\['(id|fingerprint|created_at|updated_at)'\]",
                        ],
                        exclude_paths={
                            "root['id']",
                            "root['fingerprint']",
                            "root['created_at']",
                            "root['updated_at']",
                        },
                    )
                    assert not diff
                case str():
                    assert value == library_value["name"]
                case _:
                    pytest.skip(f"not testing {type(value)}")

        else:
            assert value == library_value

        assert instance0.name == instance1.name
        assert instance0.fingerprint == instance1.fingerprint

        assert instance0.created_at == instance0.updated_at == instance1.created_at
        assert instance1.updated_at > instance1.created_at

    @pytest.mark.parametrize("target_type", [(TrailModel), (str), (int), (dict)])
    def test_upsert_identical_touched(
        self,
        trail_manager: TrailManager,
        Model: type[TrailModel],
        field_name: str,
        library_set: int,
        target_type: type[TrailRelation],
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)
        field = instance0._meta.get_field(field_name)

        value = deepcopy(
            serialize_field(
                instance0,
                field,
                target_type,
            )
        )

        instance1 = trail_manager.get_instance(
            Model,
            record,
            **serialize(instance0, target_type) | {field.name: value},
        )

        assert getattr(instance0, field.name) == getattr(instance1, field.name)

        assert instance0.name == instance1.name
        assert instance0.fingerprint == instance1.fingerprint

        assert instance0.created_at == instance0.updated_at == instance1.created_at
        assert instance1.updated_at > instance1.created_at

    @pytest.mark.parametrize("target_type", [(TrailModel), (str), (int), (dict)])
    def test_upsert_variation(
        self,
        trail_manager: TrailManager,
        Model: type[TrailModel],
        field_name: str,
        library_set: int,
        target_type: type[TrailRelation],
    ):
        record = f"{Model.record_name()}-{library_set}"
        instance0 = trail_manager.get_instance(Model, record)
        field = instance0._meta.get_field(field_name)

        value = make_tiny_change(
            serialize_field(
                instance0,
                field,
                target_type,
            )
        )

        def get_instance():
            with transaction.atomic():
                instance1 = trail_manager.get_instance(
                    Model,
                    record,
                    **serialize(instance0, target_type) | {field.name: value},
                )
                assert getattr(instance1, field.name) or True
            return instance1

        if (instance0._meta.get_field(field.name).related_model) and target_type in (
            int,
            dict,
        ):
            with pytest.raises((IntegrityError, ObjectDoesNotExist)):
                get_instance()

            return

        instance1 = get_instance()
        assert getattr(instance0, field.name) != getattr(instance1, field.name)

        assert instance0.name == instance1.name
        assert instance0.fingerprint != instance1.fingerprint

        assert instance0.created_at == instance0.updated_at
        assert instance1.created_at == instance1.updated_at
