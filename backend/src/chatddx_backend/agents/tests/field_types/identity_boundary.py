# src/chatddx_backend/agents/tests/field_types/identity_boundary.py
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, cast

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
    CoercionChoices,
    Connection,
    OutputType,
    ProviderChoices,
    SamplingParams,
    Tool,
    ToolChoices,
    ToolGroup,
    ValidationChoices,
)
from chatddx_backend.agents.models.agent import JSONSchemaField
from chatddx_backend.agents.schemas import (
    ConnectionSchema,
    OutputTypeSchema,
    SamplingParamsSchema,
    ToolGroupSchema,
    ToolSchema,
    TrailRegistry,
)

registry: TrailRegistry = TrailRegistry.from_file(
    Path(__file__).parent / "../registry/some.toml"
)


def _test_ToolGroup(value: ToolGroupSchema):
    altered_value = value.model_copy(update={"tools": _test_tools(value.tools)[1]})
    return deepcopy(value), altered_value


def _test_optional_ToolGroup(value: ToolGroupSchema | None):
    altered_value = (
        registry.get(ToolGroupSchema, "some-tool_group") if value is None else None
    )
    return deepcopy(value), altered_value


def _test_OutputType(value: OutputTypeSchema):
    altered_value = value.model_copy(
        update={"definition": _test_jsonschema(value.definition)[1]}
    )
    return deepcopy(value), altered_value


def _test_optional_OutputType(value: OutputTypeSchema | None):
    altered_value = (
        registry.get(OutputTypeSchema, "some-output_type") if value is None else None
    )
    return deepcopy(value), altered_value


def _test_SamplingParams(value: SamplingParamsSchema):
    altered_value = value.model_copy(
        update={"temperature": _test_optional_decimal(value.temperature)[1]}
    )

    return deepcopy(value), altered_value


def _test_optional_SamplingParams(value: SamplingParamsSchema | None):
    altered_value = (
        registry.get(SamplingParamsSchema, "some-sampling_params")
        if value is None
        else None
    )
    return deepcopy(value), altered_value


def _test_Connection(value: ConnectionSchema):
    altered_value = value.model_copy(update={"endpoint": _test_str(value.endpoint)[1]})
    return deepcopy(value), altered_value


def _test_optional_Connection(value: ConnectionSchema | None):
    altered_value = (
        registry.get(ConnectionSchema, "some-connection") if value is None else None
    )
    return deepcopy(value), altered_value


def _test_tools(value: list[ToolSchema]):
    tool = next(v for v in _test_optional_tool(None) if v)
    if len(value) == 0:
        return value, [tool]
    if len(value) == 1:
        _, altered_tool = _test_tool(value[0])
        return value, [altered_tool]
    return deepcopy(value), value[:1]


def _test_optional_tools(value: list[ToolSchema] | None):
    altered_value = cast(list[ToolSchema], []) if value is None else None
    return deepcopy(value), altered_value


def _test_tool(value: ToolSchema):
    altered_value = value.model_copy(
        update={
            "description": _test_optional_str(value.description)[1],
        }
    )
    return deepcopy(value), altered_value


def _test_optional_tool(value: ToolSchema | None):
    altered_value = registry.get(ToolSchema, "some-tool") if value is None else None
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


def _test_provider_type(value: ProviderChoices):
    altered_value = next(v for v in ProviderChoices if v != value)
    return value, altered_value


def _test_tool_type(value: ToolChoices):
    altered_value = next(v for v in ToolChoices if v != value)
    return value, altered_value


def _test_validation_strategy(value: ValidationChoices):
    altered_value = next(v for v in ValidationChoices if v != value)
    return value, altered_value


def _test_coercion_strategy(value: CoercionChoices):
    altered_value = next(v for v in CoercionChoices if v != value)
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
    (CharField, ProviderChoices): _test_provider_type,
    (CharField, ToolChoices): _test_tool_type,
    (CharField, ValidationChoices): _test_validation_strategy,
    (CharField, CoercionChoices): _test_coercion_strategy,
    (Connection, ConnectionSchema): _test_Connection,
    (Connection, ConnectionSchema | None): _test_optional_Connection,
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
    (OutputType, OutputTypeSchema): _test_OutputType,
    (OutputType, OutputTypeSchema | None): _test_optional_OutputType,
    (PositiveIntegerField, int): _test_int,
    (PositiveIntegerField, int | None): _test_optional_int,
    (SamplingParams, SamplingParamsSchema): _test_SamplingParams,
    (SamplingParams, SamplingParamsSchema | None): _test_optional_SamplingParams,
    (TextField, str): _test_str,
    (TextField, str | None): _test_optional_str,
    (Tool, list[ToolSchema]): _test_tools,
    (Tool, list[ToolSchema] | None): _test_optional_tools,
    (ToolGroup, ToolGroupSchema): _test_ToolGroup,
    (ToolGroup, ToolGroupSchema | None): _test_optional_ToolGroup,
    (URLField, str): _test_str,
}
