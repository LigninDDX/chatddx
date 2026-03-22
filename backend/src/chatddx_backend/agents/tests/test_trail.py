# src/chatddx_backend/agents/tests/test_trail.py
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, cast

import pytest
from django.db.models import (
    BooleanField,
    CharField,
    DecimalField,
    IntegerField,
    JSONField,
    PositiveIntegerField,
    TextField,
    URLField,
)

from chatddx_backend.agents.models import (
    Agent,
    CoercionStrategy,
    Connection,
    OutputType,
    ProviderType,
    SamplingParams,
    Tool,
    ToolGroup,
    ToolType,
    TrailModel,
    ValidationStrategy,
)
from chatddx_backend.agents.models.agent import JSONSchemaField
from chatddx_backend.agents.registry import load_registry
from chatddx_backend.agents.schema import (
    ConnectionIn,
    OutputTypeIn,
    SamplingParamsIn,
    ToolGroupIn,
    ToolIn,
    TrailInSchema,
    TrailOutSchema,
)
from chatddx_backend.agents.state import (
    model_from_schema,
    process_from_registry,
    schema_from_registry,
)

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
    for field in Model.schema_in.model_fields
]


@pytest.mark.django_db
@pytest.mark.parametrize("Model, record, field_name", fields)
@pytest.mark.time_machine(datetime(1970, 1, 1), tick=False)
def test_field_types(
    time_machine: Any,
    subtests: pytest.Subtests,
    Model: type[TrailModel],
    record: str,
    field_name: str,
):
    field = Model._meta.get_field(field_name)

    SchemaIn: type[TrailInSchema] = Model.schema_in
    SchemaOut: type[TrailOutSchema] = Model.schema_out

    db_type = field.related_model if field.related_model else field.__class__
    api_type = SchemaIn.model_fields[field_name].annotation
    test_key = (db_type, api_type)

    if test_key not in field_types:
        pytest.fail(f"No test defined for type combination {test_key} on {field_name}")

    schema_out = process_from_registry(Model, record, registry)
    schema_in = SchemaIn.model_validate(schema_out.model_dump())

    value, altered_value = field_types[test_key](getattr(schema_in, field_name))

    for value, expect_fn, msg in (
        (value, expect_update, f"apply identical value ({test_key})"),
        (altered_value, expect_create, "apply altered value"),
        (value, expect_update, "apply identical value again"),
    ):
        time_machine.shift(timedelta(days=1))
        test_schema_in = schema_in.model_copy(update={field_name: value})
        test_instance = model_from_schema(Model, test_schema_in)
        test_schema_out = SchemaOut.model_validate(test_instance)

        with subtests.test(msg=msg):
            expect_fn(SchemaIn, schema_out, test_schema_out, field_name)


def expect_update(
    SchemaIn: type[TrailInSchema],
    schema_out: TrailOutSchema,
    altered_schema_out: TrailOutSchema,
    field_name: str,
):
    schema_in = SchemaIn.model_validate(schema_out.model_dump())
    altered_schema_in = SchemaIn.model_validate(altered_schema_out.model_dump())

    assert getattr(schema_in, field_name) == getattr(altered_schema_in, field_name)

    assert schema_out.name == altered_schema_out.name
    assert schema_out.fingerprint == altered_schema_out.fingerprint

    assert (
        schema_out.created_at == schema_out.updated_at == altered_schema_out.created_at
    )
    assert schema_out.created_at < altered_schema_out.updated_at


def expect_create(
    SchemaIn: type[TrailInSchema],
    schema_out: TrailOutSchema,
    test_schema_out: TrailOutSchema,
    field_name: str,
):
    schema_in = SchemaIn.model_validate(schema_out.model_dump())
    test_schema_in = SchemaIn.model_validate(test_schema_out.model_dump())

    assert getattr(schema_in, field_name) != getattr(test_schema_in, field_name)

    if field_name == "name":
        assert schema_out.fingerprint == test_schema_out.fingerprint
    else:
        assert schema_out.name == test_schema_out.name
        assert schema_out.fingerprint != test_schema_out.fingerprint

    assert schema_out.created_at == schema_out.updated_at
    assert test_schema_out.created_at == test_schema_out.updated_at


def _test_ToolGroup(value: ToolGroupIn):
    altered_value = value.model_copy(update={"tools": _test_tools(value.tools)[1]})
    return deepcopy(value), altered_value


def _test_optional_ToolGroup(value: ToolGroupIn | None):
    altered_value = (
        schema_from_registry(ToolGroupIn, "some-tool_group", registry)
        if value is None
        else None
    )
    return deepcopy(value), altered_value


def _test_OutputType(value: OutputTypeIn):
    altered_value = value.model_copy(
        update={"definition": _test_jsonschema(value.definition)[1]}
    )
    return deepcopy(value), altered_value


def _test_optional_OutputType(value: OutputTypeIn | None):
    altered_value = (
        schema_from_registry(OutputTypeIn, "some-output_type", registry)
        if value is None
        else None
    )
    return deepcopy(value), altered_value


def _test_SamplingParams(value: SamplingParamsIn):
    altered_value = value.model_copy(
        update={"temperature": _test_optional_decimal(value.temperature)}
    )

    return deepcopy(value), altered_value


def _test_optional_SamplingParams(value: SamplingParamsIn | None):
    altered_value = (
        schema_from_registry(SamplingParamsIn, "some-sampling_params", registry)
        if value is None
        else None
    )
    return deepcopy(value), altered_value


def _test_Connection(value: ConnectionIn):
    altered_value = value.model_copy(update={"endpoint": _test_str(value.endpoint)[1]})
    return deepcopy(value), altered_value


def _test_optional_Connection(value: ConnectionIn | None):
    altered_value = (
        schema_from_registry(ConnectionIn, "some-connection", registry)
        if value is None
        else None
    )
    return deepcopy(value), altered_value


def _test_tools(value: list[ToolIn]):
    tool = next(v for v in _test_optional_tool(None) if v)
    if len(value) == 0:
        return value, [tool]
    if len(value) == 1:
        _, altered_tool = _test_tool(value[0])
        return value, [altered_tool]
    return reversed(value), value[1:]


def _test_optional_tools(value: list[ToolIn] | None):
    altered_value = cast(list[ToolIn], []) if value is None else None
    return deepcopy(value), altered_value


def _test_tool(value: ToolIn):
    altered_value = value.model_copy(
        update={
            "description": _test_optional_str(value.description)[1],
        }
    )
    return deepcopy(value), altered_value


def _test_optional_tool(value: ToolIn | None):
    altered_value = (
        schema_from_registry(ToolIn, "some-tool", registry) if value is None else None
    )
    return deepcopy(value), altered_value


def _test_dict_str_decimal(value: dict[str, Decimal]):
    return deepcopy(value), value | {"_": _test_optional_decimal(None)[1]}


def _test_jsonschema(value: dict[str, Any]):
    altered_value = value | {
        "additionalProperties": _test_bool(value.get("additionalProperties", False))[1]
    }

    return deepcopy(value), altered_value


def _test_optional_jsonschema(value: dict[str, Any] | None):
    altered_value = cast(dict[str, Any], {}) if value is None else None
    return deepcopy(value), altered_value


def _test_dict_str_any(value: dict[str, Any]):
    return deepcopy(value), value | {"_": "'"}


def _test_optional_dict_str_any(value: dict[str, Any] | None):
    altered_value = cast(dict[str, Any], {}) if value is None else None
    return deepcopy(value), altered_value


def _test_list_str(value: list[str]):
    if len(value) == 0:
        return value, [_test_optional_str(None)[1]]
    if len(value) == 1:
        return value, _test_str(value[0])[1]

    return deepcopy(value), reversed(value)


def _test_optional_list_str(value: list[str] | None):
    altered_value = cast(list[str], []) if value is None else None
    return deepcopy(value), altered_value


def _test_provider_type(value: ProviderType):
    altered_value = next(v for v in ProviderType if v != value)
    return value, altered_value


def _test_tool_type(value: ToolType):
    altered_value = next(v for v in ToolType if v != value)
    return value, altered_value


def _test_validation_strategy(value: ValidationStrategy):
    altered_value = next(v for v in ValidationStrategy if v != value)
    return value, altered_value


def _test_optional_coercion_strategy(value: CoercionStrategy):
    altered_value = next(v for v in CoercionStrategy if v != value)
    return value, altered_value


def _test_int(value: int):
    altered_value = 0 if value else 1
    return value, altered_value


def _test_optional_int(value: int | None):
    altered_value = 0 if value is None else None
    return value, altered_value


def _test_decimal(value: Decimal):
    altered_value = Decimal(0) if value else Decimal("0.1")
    return value, altered_value


def _test_optional_decimal(value: Decimal | None):
    altered_value = Decimal(0) if value is None else None
    return value, altered_value


def _test_str(value: str):
    altered_value = "" if value else "'"
    return value, altered_value


def _test_optional_str(value: str | None):
    altered_value = "" if value is None else None
    return value, altered_value


def _test_bool(value: bool):
    return value, not value


field_types: dict[Any, Callable[[Any], tuple[Any, Any]]] = {
    (BooleanField, bool): _test_bool,
    (CharField, str): _test_str,
    (CharField, str | None): _test_optional_str,
    (CharField, ProviderType): _test_provider_type,
    (CharField, ToolType): _test_tool_type,
    (CharField, ValidationStrategy): _test_validation_strategy,
    (CharField, CoercionStrategy | None): _test_optional_coercion_strategy,
    (Connection, ConnectionIn): _test_Connection,
    (Connection, ConnectionIn | None): _test_optional_Connection,
    (DecimalField, Decimal): _test_decimal,
    (DecimalField, Decimal | None): _test_optional_decimal,
    (IntegerField, int): _test_int,
    (IntegerField, int | None): _test_optional_int,
    (JSONField, dict[str, Decimal]): _test_dict_str_decimal,
    (JSONField, dict[str, Any] | None): _test_optional_dict_str_any,
    (JSONField, dict[str, Any]): _test_dict_str_any,
    (JSONField, list[str] | None): _test_optional_list_str,
    (JSONField, list[str]): _test_list_str,
    (JSONSchemaField, dict[str, Any] | None): _test_optional_jsonschema,
    (JSONSchemaField, dict[str, Any]): _test_jsonschema,
    (OutputType, OutputTypeIn): _test_OutputType,
    (OutputType, OutputTypeIn | None): _test_optional_OutputType,
    (PositiveIntegerField, int): _test_int,
    (PositiveIntegerField, int | None): _test_optional_int,
    (SamplingParams, SamplingParamsIn): _test_SamplingParams,
    (SamplingParams, SamplingParamsIn | None): _test_optional_SamplingParams,
    (TextField, str): _test_str,
    (TextField, str | None): _test_optional_str,
    (Tool, list[ToolIn]): _test_tools,
    (Tool, list[ToolIn] | None): _test_optional_tools,
    (ToolGroup, ToolGroupIn): _test_ToolGroup,
    (ToolGroup, ToolGroupIn | None): _test_optional_ToolGroup,
    (URLField, str): _test_str,
}
