from __future__ import annotations

from typing import Any, TypedDict


class LLMUsagePayload(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model_name: str | None
    model_provider: str | None


def extract_token_usage(raw_message: Any) -> dict[str, int]:
    if raw_message is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if isinstance(raw_message, dict):
        usage = raw_message.get("usage_metadata", {}) or {}
        response_metadata = raw_message.get("response_metadata", {}) or {}
    else:
        usage = getattr(raw_message, "usage_metadata", None) or {}
        response_metadata = getattr(raw_message, "response_metadata", None) or {}

    nested_usage = response_metadata.get("usage", {}) if isinstance(response_metadata, dict) else {}
    token_usage = response_metadata.get("token_usage", {}) if isinstance(response_metadata, dict) else {}

    input_tokens = (
        usage.get("input_tokens")
        or nested_usage.get("input_tokens")
        or nested_usage.get("inputTokens")
        or token_usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or 0
    )
    output_tokens = (
        usage.get("output_tokens")
        or nested_usage.get("output_tokens")
        or nested_usage.get("outputTokens")
        or token_usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or 0
    )
    total_tokens = (
        usage.get("total_tokens")
        or nested_usage.get("total_tokens")
        or nested_usage.get("totalTokens")
        or token_usage.get("total_tokens")
        or (int(input_tokens) + int(output_tokens))
    )

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
    }


def extract_callback_token_usage(usage_metadata: Any) -> dict[str, int]:
    if not isinstance(usage_metadata, dict):
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if (
        "input_tokens" in usage_metadata
        or "output_tokens" in usage_metadata
        or "total_tokens" in usage_metadata
    ):
        input_tokens = int(usage_metadata.get("input_tokens", 0) or 0)
        output_tokens = int(usage_metadata.get("output_tokens", 0) or 0)
        total_tokens = int(usage_metadata.get("total_tokens", input_tokens + output_tokens) or 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    for value in usage_metadata.values():
        if not isinstance(value, dict):
            continue
        input_tokens += int(value.get("input_tokens", 0) or 0)
        output_tokens += int(value.get("output_tokens", 0) or 0)
        total_tokens += int(value.get("total_tokens", 0) or 0)

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def extract_model_metadata(
    raw_message: Any,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict[str, str | None]:
    response_metadata = {}
    if isinstance(raw_message, dict):
        response_metadata = raw_message.get("response_metadata", {}) or {}
    elif raw_message is not None:
        response_metadata = getattr(raw_message, "response_metadata", None) or {}

    model_name = None
    model_provider = None

    if isinstance(response_metadata, dict):
        model_name = response_metadata.get("model_name") or response_metadata.get("model")
        model_provider = response_metadata.get("model_provider") or response_metadata.get("provider")

    return {
        "model_name": str(model_name or fallback_model) if (model_name or fallback_model) else None,
        "model_provider": str(model_provider or fallback_provider) if (model_provider or fallback_provider) else None,
    }


def build_usage_payload(
    callback_usage_metadata: Any,
    raw_message: Any,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> LLMUsagePayload:
    callback_usage = extract_callback_token_usage(callback_usage_metadata)
    raw_usage = extract_token_usage(raw_message)
    tokens = callback_usage if callback_usage.get("total_tokens", 0) > 0 else raw_usage
    model_meta = extract_model_metadata(
        raw_message,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )

    return {
        "input_tokens": int(tokens.get("input_tokens", 0) or 0),
        "output_tokens": int(tokens.get("output_tokens", 0) or 0),
        "total_tokens": int(tokens.get("total_tokens", 0) or 0),
        "model_name": model_meta.get("model_name"),
        "model_provider": model_meta.get("model_provider"),
    }
