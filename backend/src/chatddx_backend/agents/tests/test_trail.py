# src/chatddx_backend/agents/tests/test_trail.py
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

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
    as_model_instance,
    from_registry,
    load_registry,
)

registry: dict[str, Any] = load_registry(Path(__file__).parent / "registry.toml")

models = (
    Connection,
    SamplingParams,
    ToolGroup,
    Tool,
    OutputType,
    Agent,
)

fields = [(Model, field) for Model in models for field in Model.schema_in.model_fields]


def _test_ToolGroup(value: ToolGroupIn):
    altered_value = value.model_copy(update={"instructions": value.instructions + "'"})
    return deepcopy(value), altered_value


def _test_optional_ToolGroup(value: ToolGroupIn):
    tool_group = ToolGroupIn(
        name="new tool group",
        instructions="no tools",
        tools=[],
    )
    return _test_ToolGroup(value) if value else (value, tool_group)


def _test_OutputType(value: OutputTypeIn):
    altered_value = value.model_copy(update={"definition": value.definition | {"k": 1}})
    return deepcopy(value), altered_value


def _test_optional_OutputType(value: OutputTypeIn):
    output_type = OutputTypeIn(
        name="new output type",
        definition={},
    )
    return _test_OutputType(value) if value else (value, output_type)


def _test_SamplingParams(value: SamplingParamsIn):
    altered_value = value.model_copy(
        update={"temperature": (value.temperature or Decimal("0")) + Decimal("0.1")}
    )

    return deepcopy(value), altered_value


def _test_optional_SamplingParams(value: SamplingParamsIn):
    sampling_params = SamplingParamsIn(
        name="new sampling params",
        temperature=Decimal("1"),
    )
    return _test_SamplingParams(value) if sampling_params else (value, sampling_params)


def _test_Connection(value: ConnectionIn):
    altered_value = value.model_copy(update={"endpoint": value.endpoint + "'"})
    return deepcopy(value), altered_value


def _test_optional_Connection(value: ConnectionIn):
    connection = ConnectionIn(
        name="new connection",
        model="qwen",
        provider=ProviderType.VLLM,
        endpoint="/",
    )
    return _test_Connection(value) if value else (value, connection)


def _test_tools(value: list[ToolIn]):
    altered_value = [
        value[0].model_copy(update={"description": value[0].description + "'"})
    ] + value[1:]

    return deepcopy(value), altered_value


def _test_optional_tools(value: list[ToolIn] | None):
    tools = list(_test_optional_tool(None))
    return _test_tools(value) if value else (value, tools)


def _test_tool(value: ToolIn):
    altered_value = value.model_copy(update={"description": value.description + "'"})
    return deepcopy(value), altered_value


def _test_optional_tool(value: ToolIn | None):
    tool = ToolIn(
        name="new tool",
        description="a new tool",
        type=ToolType.FUNCTION,
        parameters={},
    )
    return _test_tool(value) if value else (value, tool)


def _test_provider_type(value: str):
    return value, ProviderType.OLLAMA


def _test_tool_type(value: str):
    return value, ToolType.WEB_SEARCH


def _test_validation_strategy(value: str):
    return value, ValidationStrategy.CRASH


def _test_optional_coercion_strategy(value: str):
    return value, CoercionStrategy.PROMPTED


def _test_dict_str_decimal(value: dict[str, Decimal]):
    return deepcopy(value), value | {"k": Decimal("0.1")}


def _test_dict_str_any(value: dict[str, Any]):
    return deepcopy(value), value | {"k": "'"}


def _test_optional_dict_str_any(value: dict[str, Any] | None):
    return _test_dict_str_any(value) if value else (value, {"k": "'"})


def _test_list_str(value: list[str]):
    return deepcopy(value), value + ["'"]


def _test_optional_list_str(value: list[str] | None):
    return _test_list_str(value) if value else (value, ["'"])


def _test_int(value: int):
    return value, value + 1


def _test_optional_int(value: int | None):
    return _test_int(value) if value else (value, 1)


def _test_decimal(value: Decimal):
    return value, value + Decimal("0.1")


def _test_optional_decimal(value: Decimal | None):
    return _test_decimal(value) if value else (value, Decimal("0.1"))


def _test_str(value: str):
    return value, value + "'"


def _test_optional_str(value: str):
    return _test_str(value) if value else (value, "'")


def _test_bool(value: bool):
    return value, not value


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


@pytest.mark.django_db
@pytest.mark.parametrize("Model, field_name", fields)
class TestFieldTypes:
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
        (OutputType, OutputTypeIn): _test_OutputType,
        (OutputType, OutputTypeIn | None): _test_optional_OutputType,
        (PositiveIntegerField, int): _test_int,
        (PositiveIntegerField, int | None): _test_optional_int,
        (SamplingParams, SamplingParamsIn): _test_SamplingParams,
        (SamplingParams, SamplingParamsIn | None): _test_optional_SamplingParams,
        (TextField, str): _test_str,
        (Tool, list[ToolIn]): _test_tools,
        (Tool, list[ToolIn] | None): _test_optional_tools,
        (ToolGroup, ToolGroupIn): _test_ToolGroup,
        (ToolGroup, ToolGroupIn | None): _test_optional_ToolGroup,
        (URLField, str): _test_str,
    }

    @pytest.mark.time_machine(datetime(1970, 1, 1), tick=False)
    def test_field_types(
        self,
        time_machine: Any,
        subtests: pytest.Subtests,
        Model: type[TrailModel],
        field_name: str,
    ):
        field = Model._meta.get_field(field_name)

        SchemaIn: type[TrailInSchema] = Model.schema_in
        SchemaOut: type[TrailOutSchema] = Model.schema_out

        db_type = field.related_model if field.related_model else field.__class__
        api_type = SchemaIn.model_fields[field_name].annotation
        test_key = (db_type, api_type)

        if test_key not in self.field_types:
            pytest.fail(
                f"No test defined for type combination {test_key} on {field_name}"
            )

        record = f"{SchemaIn.record_type}-1"
        schema_out = from_registry(Model, record, registry)
        schema_in = SchemaIn.model_validate(schema_out.model_dump())

        value, altered_value = self.field_types[test_key](
            getattr(schema_in, field_name)
        )

        for value, expect_fn, msg in (
            (value, expect_update, f"apply identical value ({test_key})"),
            (altered_value, expect_create, "apply altered value"),
            (value, expect_update, "apply identical value again"),
        ):
            time_machine.shift(timedelta(days=1))
            test_schema_in = schema_in.model_copy(update={field_name: value})
            test_instance = as_model_instance(Model, test_schema_in)
            test_schema_out = SchemaOut.model_validate(test_instance)

            with subtests.test(msg=msg):
                expect_fn(SchemaIn, schema_out, test_schema_out, field_name)
