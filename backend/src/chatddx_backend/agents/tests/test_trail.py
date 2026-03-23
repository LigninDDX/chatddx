# src/chatddx_backend/agents/tests/test_trail.py
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from chatddx_backend.agents.models import (
    Agent,
    Connection,
    OutputType,
    SamplingParams,
    Tool,
    ToolGroup,
    TrailModel,
)
from chatddx_backend.agents.registry import load_registry
from chatddx_backend.agents.schema import (
    TrailSchema,
    TrailSpec,
)
from chatddx_backend.agents.state import (
    schema_from_spec,
    spec_from_registry,
    spec_from_schema,
)
from chatddx_backend.agents.tests.field_types import identity_boundary

registry: dict[str, Any] = load_registry(
    Path(__file__).parent / "registry/test-trail.toml"
)

models = (
    (Connection, "connection-1"),
    (SamplingParams, "sampling_params-1"),
    (ToolGroup, "tool_group-1"),
    (Tool, "tool-1"),
    (OutputType, "output_type-1"),
    (Agent, "agent-1"),
    (Agent, "dice-game"),
    (Agent, "test-tools-prime"),
)

fields = [
    (Model, record, field)
    for Model, record in models
    for field in Model.Schema.model_fields
]


@pytest.mark.django_db
@pytest.mark.parametrize("Model, record, field_name", fields)
@pytest.mark.time_machine(datetime(1970, 1, 1), tick=False)
def test_identity_boundary(
    time_machine: Any,
    subtests: pytest.Subtests,
    Model: type[TrailModel],
    record: str,
    field_name: str,
):
    field = Model._meta.get_field(field_name)

    db_type = field.related_model if field.related_model else field.__class__
    api_type = Model.Schema.model_fields[field_name].annotation
    test_key = (db_type, api_type)

    if test_key not in identity_boundary.field_types:
        pytest.fail(f"No test defined for type combination {test_key} on {field_name}")

    spec = spec_from_registry(Model, Model.Spec, record, registry)
    schema = schema_from_spec(Model.Schema, spec)

    value, altered_value = identity_boundary.field_types[test_key](
        getattr(schema, field_name)
    )

    for value, expect_fn, msg in (
        (value, expect_identical, f"apply identical value ({test_key})"),
        (altered_value, expect_altered, "apply altered value"),
        (value, expect_identical, "apply identical value again"),
    ):
        time_machine.shift(timedelta(days=1))
        test_schema = schema.model_copy(update={field_name: value})
        test_spec = spec_from_schema(Model, Model.Spec, test_schema)

        with subtests.test(msg=msg):
            expect_fn(Model.Schema, spec, test_spec, field_name)


def expect_identical(
    Schema: type[TrailSchema],
    spec: TrailSpec,
    test_spec: TrailSpec,
    field_name: str,
):
    schema = schema_from_spec(Schema, spec)
    test_schema = schema_from_spec(Schema, test_spec)

    assert getattr(schema, field_name) == getattr(test_schema, field_name)

    assert spec.name == test_spec.name
    assert spec.fingerprint == test_spec.fingerprint

    assert spec.created_at == spec.updated_at == test_spec.created_at
    assert spec.created_at < test_spec.updated_at


def expect_altered(
    Schema: type[TrailSchema],
    spec: TrailSpec,
    test_spec: TrailSpec,
    field_name: str,
):
    schema = schema_from_spec(Schema, spec)
    test_schema = schema_from_spec(Schema, test_spec)

    assert getattr(schema, field_name) != getattr(test_schema, field_name)

    if field_name == "name":
        assert spec.name != test_spec.name
        assert spec.fingerprint == test_spec.fingerprint
    else:
        assert spec.name == test_spec.name
        assert spec.fingerprint != test_spec.fingerprint

    assert spec.created_at == spec.updated_at
    assert test_spec.created_at == test_spec.updated_at
