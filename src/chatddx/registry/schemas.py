from typing import Any

from pydantic import BaseModel, ValidationInfo, model_validator

Record = dict[str, Any]
DictRegistry = dict[str, Record]


class ParseError(Exception):
    pass


class RegistryInstance(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def parse_instance(cls, v: Any, info: ValidationInfo) -> Any:
        if info.context is None:
            return v

        record = info.context.get_record(cls, info.context)

        match v:
            case str():
                return {"name": v} | record[v]
            case list():
                base_data = record[v[0]] | {
                    "name": v[0],
                    "extends": v[1:],
                }
            case dict():
                base_data = v
            case _:
                raise ParseError(f"unexpected data type {type(v)}")

        if not base_data.get("extends"):
            return base_data

        if isinstance(base_data["extends"], str):
            base_data["extends"] = [base_data["extends"]]

        for ext_name in base_data["extends"]:
            ext_data = record[ext_name]
            base_data["name"] += "|" + ext_name
            base_data = ext_data | base_data

        return base_data


class BaseRegistry(BaseModel):
    pass
