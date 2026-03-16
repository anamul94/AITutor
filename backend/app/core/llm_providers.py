from __future__ import annotations

import os
from typing import Any

from botocore.config import Config
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

load_dotenv()


def _resolve_provider() -> str:
    provider = (os.getenv("LLM_PROVIDER") or "bedrock").strip().lower()
    if provider in {"openai_compatible", "openai-compatible", "openai"}:
        return "openai-compatible"
    return "bedrock"


def _create_bedrock_llm() -> tuple[Any, dict[str, str]]:
    model_id = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
    region_name = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    provider = None
    if model_id and model_id.startswith("arn:aws:bedrock"):
        parts = model_id.split("/")
        if len(parts) > 1:
            provider = parts[-1].split(".")[0]

    read_timeout = int(os.getenv("LLM_READ_TIMEOUT", "240"))
    connect_timeout = int(os.getenv("LLM_CONNECT_TIMEOUT", "20"))
    max_attempts = int(os.getenv("LLM_MAX_RETRIES", "3"))

    my_config = Config(
        read_timeout=read_timeout,
        connect_timeout=connect_timeout,
        retries={
            "max_attempts": max_attempts,
            "mode": "standard",
        },
    )

    kwargs = {
        "model_id": model_id,
        "region_name": region_name,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
        "config": my_config,
    }
    max_tokens = os.getenv("LLM_MAX_TOKENS")
    if max_tokens:
        kwargs["max_tokens"] = int(max_tokens)
    if provider:
        kwargs["provider"] = provider

    return ChatBedrockConverse(**kwargs), {
        "provider": "bedrock",
        "configured_model": model_id,
    }


def _create_openai_compatible_llm() -> tuple[Any, dict[str, str]]:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI-compatible provider selected, but langchain-openai is not installed. "
            "Install it and retry."
        ) from exc

    model_name = os.getenv("OPENAI_COMPAT_MODEL_ID", "glm-4.7-flash:latest")
    api_key = (
        os.getenv("OPENAI_COMPAT_API_KEY")
        or os.getenv("OPEN_ROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "OpenAI-compatible provider selected, but no API key found. "
            "Set OPENAI_COMPAT_API_KEY or OPEN_ROUTER_API_KEY or OPENAI_API_KEY."
        )

    base_url = os.getenv("OPENAI_COMPAT_BASE_URL", "https://openrouter.ai/api/v1")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
    )
    max_tokens = os.getenv("LLM_MAX_TOKENS")
    if max_tokens:
        llm = llm.bind(max_tokens=int(max_tokens))

    return llm, {
        "provider": "openai-compatible",
        "configured_model": model_name,
    }


def get_llm_client() -> tuple[Any, dict[str, str]]:
    provider = _resolve_provider()
    if provider == "openai-compatible":
        return _create_openai_compatible_llm()
    return _create_bedrock_llm()


def get_llm() -> Any:
    llm, _ = get_llm_client()
    return llm
