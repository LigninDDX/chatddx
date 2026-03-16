# src/chatddx_backend/agents/managers.py
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type, TypeVar

import tomli

from chatddx_backend.agents.models import (
    RelatedArrayField,
    Tool,
    ToolGroup,
    TrailModel,
)

TrailModelT = TypeVar("TrailModelT", bound=TrailModel)


@dataclass
class TrailManager:
    library: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrailManager:
        return cls(library=deepcopy(data))

    @classmethod
    def from_toml(cls, path: Path) -> TrailManager:
        with path.open("rb") as f:
            return cls(library=tomli.load(f))

    def _get_values(self, cls: Type[TrailModelT], name: str) -> dict[str, Any]:
        record_name = cls.record_name()
        model_data = self.library.get(record_name, {})

        if name not in model_data:
            raise ValueError(f"'{name}' not found in {record_name}")

        return self.library[record_name][name].copy()

    def get_instance(
        self,
        cls: Type[TrailModelT],
        *args: str,
        **kwargs: Any,
    ) -> TrailModelT:
        name = kwargs.get("name", args[0])

        if args[0] != name:
            raise ValueError(
                f"the first argument ({args[0]}) must match keyword argument 'name' ({name}) if both are defined"
            )

        values = self._get_values(cls, name) | kwargs | {"name": name}

        for field in cls._meta.concrete_fields:
            if isinstance(field, RelatedArrayField):
                values = self.normalize_related_array(
                    field.name,
                    values,
                    field.related_model,
                )

            if field.many_to_one or field.one_to_one:
                values = self.normalize_related(
                    field.name,
                    values,
                    field.related_model,
                )

        return cls.upsert(**values)  # type: ignore

    def normalize_related_array(
        self, field_name: str, values: dict[str, Any], related_model: Type[TrailModelT]
    ) -> dict[str, Any]:
        value: list[int] = []
        values = values.copy()
        for item in values.get(field_name, []):
            if isinstance(item, str):
                value.append(self.get_instance(related_model, item).pk)
            if isinstance(item, int):
                value.append(item)
            if isinstance(item, TrailModel):
                value.append(item.pk)

        values[field_name] = value

        return values

    def normalize_related(
        self, field_name: str, values: dict[str, Any], related_model: Type[TrailModelT]
    ) -> dict[str, Any]:
        value = values.get(field_name, None)
        if isinstance(value, str):
            values[field_name] = self.get_instance(related_model, value)
        if isinstance(value, int):
            del values[field_name]
            values[field_name + "_id"] = value
        return values
