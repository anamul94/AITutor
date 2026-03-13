from __future__ import annotations

from typing import Any

from app.agents.dsa_learn_agent import build_dsa_learn_prompt_inputs, generate_dsa_learn_turn
from app.agents.dsa_solve_agent import build_dsa_solve_prompt_inputs, generate_dsa_solve_turn
from app.core.llm_usage import LLMUsagePayload

COACH_DEFAULT_MESSAGE = (
    "Please coach me through this step by step. Ask guiding questions and avoid giving the full solution too early."
)


def build_dsa_coaching_prompt_inputs(
    *,
    coaching_mode: str,
    topic: str,
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
    history_excerpt: str | None,
    last_user_message: str,
) -> dict[str, str]:
    normalized_mode = (coaching_mode or "").strip().lower()
    if normalized_mode == "learn_topic":
        return build_dsa_learn_prompt_inputs(
            topic=topic,
            problem_statement=problem_statement,
            prior_knowledge=prior_knowledge,
            history_excerpt=history_excerpt,
            last_user_message=last_user_message,
        )
    return build_dsa_solve_prompt_inputs(
        topic=topic,
        problem_statement=problem_statement,
        prior_knowledge=prior_knowledge,
        learner_attempt=learner_attempt,
        history_excerpt=history_excerpt,
        last_user_message=last_user_message,
    )


async def generate_dsa_coaching_turn(
    *,
    coaching_mode: str,
    topic: str,
    language: str = "english",
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
    history_excerpt: str | None,
    user_message: str,
    thread_id: str,
) -> tuple[str, dict[str, Any], list[dict[str, str]], LLMUsagePayload]:
    normalized_mode = (coaching_mode or "").strip().lower()
    if normalized_mode == "learn_topic":
        return await generate_dsa_learn_turn(
            topic=topic,
            language=language,
            problem_statement=problem_statement,
            prior_knowledge=prior_knowledge,
            history_excerpt=history_excerpt,
            user_message=user_message,
            thread_id=thread_id,
        )
    return await generate_dsa_solve_turn(
        topic=topic,
        language=language,
        problem_statement=problem_statement,
        prior_knowledge=prior_knowledge,
        learner_attempt=learner_attempt,
        history_excerpt=history_excerpt,
        user_message=user_message,
        thread_id=thread_id,
    )
