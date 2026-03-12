from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


def response_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()

    return str(content or "")


def extract_json_object_text(raw_text: str) -> str:
    text = (raw_text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


def parse_pydantic_from_response(response: Any, schema: type[TModel]) -> TModel:
    # Bedrock with_structured_output uses tool-calling: content is '' but
    # the schema args live in tool_calls[0]["args"] as a plain dict.
    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls and isinstance(tool_calls, list):
        args = tool_calls[0].get("args") if tool_calls else None
        if isinstance(args, dict):
            return schema.model_validate(args)

    content = response_content_to_text(getattr(response, "content", response))
    json_text = extract_json_object_text(content)
    return schema.model_validate_json(json_text)
