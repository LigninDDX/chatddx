# src/chatddx_backend/agents/tests/test_trail.py
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from django.db import ProgrammingError

from chatddx_backend.agents import type_map
from chatddx_backend.agents.models import AgentModel
from chatddx_backend.agents.schemas import (
    AgentSchema,
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolSchema,
    TrailRegistry,
)
from chatddx_backend.agents.tests.field_types import identity_boundary
from chatddx_backend.agents.trail import (
    TrailModel,
    TrailSchema,
    TrailSpec,
    model_from_schema,
    schema_from_spec,
    spec_from_model,
)

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "registry/test-registry.toml"
)

schemas = (
    (ConnectionSchema, "connection-1"),
    (SamplingParamsSchema, "sampling_params-1"),
    (ToolGroupSchema, "tool_group-1"),
    (ToolSchema, "tool-1"),
    (OutputTypeSchema, "output_type-1"),
    (AgentSchema, "agent-1"),
    (AgentSchema, "agent-2"),
    (AgentSchema, "agent-3"),
)

fields = [
    (Schema, record, field)
    for Schema, record in schemas
    for field in Schema.model_fields
]


@pytest.mark.asyncio
@pytest.mark.django_db()
@pytest.mark.parametrize("Schema, record, field_name", fields)
@pytest.mark.time_machine(datetime(1970, 1, 1), tick=False)
async def test_identity_boundary(
    time_machine: Any,
    subtests: pytest.Subtests,
    Schema: type[TrailSchema],
    record: str,
    field_name: str,
):
    Model = type_map.resolve(Schema, TrailModel)
    Spec = type_map.resolve(Schema, TrailSpec)

    field = Model._meta.get_field(field_name)

    db_type = field.related_model if field.related_model else field.__class__
    api_type = Schema.model_fields[field_name].annotation
    test_key = (db_type, api_type)

    if test_key not in identity_boundary.field_types:
        pytest.fail(f"No test defined for type combination {test_key} on {field_name}")

    schema = registry.get(Schema, record)
    model = await model_from_schema(Model, schema)
    spec = spec_from_model(Spec, model)

    schema = schema_from_spec(Schema, spec)

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
        test_model = await model_from_schema(Model, test_schema)
        test_spec = spec_from_model(Spec, test_model)

        with subtests.test(msg=msg):
            expect_fn(Schema, spec, test_spec, field_name)


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


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_immutability_trigger():
    agent_schema = registry.get(AgentSchema, "agent-1")
    agent_model = await model_from_schema(AgentModel, agent_schema)

    agent_model.updated_at = datetime.now()
    await agent_model.asave()

    agent_model.instructions += "a"
    with pytest.raises(ProgrammingError):
        await agent_model.asave()
