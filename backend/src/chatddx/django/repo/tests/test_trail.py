# src/chatddx_backend/agents/tests/test_trail.py
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from django.db import ProgrammingError

from chatddx_backend.agents import trail_map
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
@pytest.mark.django_db
@pytest.mark.parametrize("Schema, record, field_name", fields)
@pytest.mark.time_machine(datetime(1970, 1, 1), tick=False)
async def test_identity_boundary(
    time_machine: Any,
    Schema: type[TrailSchema],
    record: str,
    field_name: str,
):
    Model = trail_map.resolve(Schema, TrailModel)
    Spec = trail_map.resolve(Schema, TrailSpec)

    field = Model._meta.get_field(field_name)

    associated_model = getattr(field, "associated_model", None)
    db_type = field.related_model or associated_model or field.__class__
    api_type = Schema.model_fields[field_name].annotation
    test_key = (db_type, api_type)

    if test_key not in identity_boundary.field_types:
        pytest.fail(f"No test defined for type combination {test_key} on {field_name}")

    schema = registry.get_by_type(Schema, record)
    model = await model_from_schema(Model, schema)
    spec = spec_from_model(Spec, model)

    value, altered_value = identity_boundary.field_types[test_key](
        getattr(schema, field_name)
    )

    for value, altered in (
        (value, False),
        (altered_value, True),
        (value, False),
    ):
        time_machine.shift(timedelta(days=1))
        raw_copy = schema.model_copy(update={field_name: value})

        test_schema = Schema.model_validate(raw_copy.model_dump())
        test_model = await model_from_schema(Model, test_schema)
        test_spec = spec_from_model(Spec, test_model)

        if not altered:
            assert schema.fingerprint == test_schema.fingerprint
            assert model.fingerprint == test_model.fingerprint
            assert spec.fingerprint == test_spec.fingerprint

        if altered:
            assert schema.fingerprint != test_schema.fingerprint
            assert model.fingerprint != test_model.fingerprint
            assert spec.fingerprint != test_spec.fingerprint


@pytest.mark.asyncio
@pytest.mark.django_db()
async def test_immutability_trigger():
    agent_schema = registry.get_by_type(AgentSchema, "agent-1")
    agent_model = await model_from_schema(AgentModel, agent_schema)

    with pytest.raises(ProgrammingError):
        await agent_model.asave()
