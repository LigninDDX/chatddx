from typing import Sequence

from pydantic_ai import (
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
    ModelRequestPart,
    ModelResponsePart,
    ToolCallPart,
    ToolReturnPart,
)


def get_part_content(
    parts: Sequence[ModelRequestPart | ModelResponsePart],
    PartType: type[ModelRequestPart | ModelResponsePart],
):
    content = ""
    for part in parts:
        if isinstance(part, PartType):
            if isinstance(part, (ToolCallPart, BuiltinToolCallPart)):
                content += f"{part.tool_name}: {part.args_as_json_str()}"
            elif isinstance(part, (ToolReturnPart, BuiltinToolReturnPart)):
                content += f"{part.tool_name}: {part.content}"
            else:
                match part.content:
                    case str():
                        content += part.content
                    case _:
                        raise ValueError("unsupported part type")
    return content
