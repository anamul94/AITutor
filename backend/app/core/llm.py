from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from app.agents.course_agent import build_course_syllabus_prompt_inputs, generate_course_syllabus
from app.agents.dsa_coach_agent import build_dsa_coaching_prompt_inputs, generate_dsa_coaching_turn
from app.agents.lesson_agent import build_lesson_prompt_inputs, generate_lesson_content
from app.agents.lesson_quiz_agent import build_lesson_quiz_prompt_inputs, generate_lesson_quiz
from app.core.llm_providers import get_llm
from app.core.llm_usage import (
    build_usage_payload,
    extract_callback_token_usage,
    extract_model_metadata,
    extract_token_usage,
)

load_dotenv()


def get_ollama_llm() -> Any:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise RuntimeError("langchain-ollama is not installed.") from exc

    model_name = os.getenv("OLLAMA_MODEL_NAME", "glm-4.7-flash:latest")
    return ChatOllama(model=model_name, temperature=0.1)


__all__ = [
    "get_llm",
    "get_ollama_llm",
    "build_course_syllabus_prompt_inputs",
    "build_dsa_coaching_prompt_inputs",
    "build_lesson_prompt_inputs",
    "build_lesson_quiz_prompt_inputs",
    "extract_token_usage",
    "extract_callback_token_usage",
    "extract_model_metadata",
    "build_usage_payload",
    "generate_course_syllabus",
    "generate_dsa_coaching_turn",
    "generate_lesson_content",
    "generate_lesson_quiz",
]
