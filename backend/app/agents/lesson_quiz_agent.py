from __future__ import annotations

from typing import Optional

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_json import parse_pydantic_from_response
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload
from app.schemas.course import GeneratedLessonQuizSchema

LESSON_QUIZ_SYSTEM_PROMPT = """You are an expert assessment designer.

Primary objective:
- Generate high-quality multiple-choice quiz questions based strictly on the lesson content and metadata.

Quiz contract:
1. Generate between 5 and 10 multiple-choice questions.
2. Each question must have exactly 4 options.
3. Exactly one option is correct per question.
4. `correct_answer_index` must be an integer from 0 to 3.
5. Include a concise explanation for each answer.
6. Mix difficulty across the set: recall, application, and reasoning/troubleshooting.
7. Distractors must be plausible and close to common misconceptions.
8. Do not invent facts outside the provided lesson content.
9. Generate learner-facing text in the requested language.
10. Keep code syntax, API names, and proper nouns unchanged when needed.
"""

LESSON_QUIZ_USER_PROMPT = """Course: {course_title}
Module: {module_title}
Lesson: {lesson_title}
Lesson Description Scope: {lesson_description_context}
Preferred Level: {preferred_level_context}
Learning Goal: {learning_goal_context}
Output Language: {language_context}

Lesson content to assess:
{lesson_content}

Generate only JSON that follows the schema contract."""

LESSON_QUIZ_JSON_RULES = """
Output format requirements:
- Return ONLY valid JSON.
- Do NOT use markdown code fences.
- Do NOT add any text before or after the JSON.
- JSON must have a top-level key named "quiz".
- "quiz" must be an array of objects.
- Each quiz object must include:
  - "question" (string)
  - "options" (array of exactly 4 strings)
  - "correct_answer_index" (integer 0-3)
  - "explanation" (string)
- `quiz` must contain 5 to 10 objects.
"""


def build_lesson_quiz_prompt_inputs(
    course_title: str,
    module_title: str,
    lesson_title: str,
    lesson_content: str,
    lesson_description: Optional[str] = None,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, str]:
    normalized_level = preferred_level.strip().lower() if preferred_level else ""
    if normalized_level not in {"beginner", "intermediate", "advanced"}:
        normalized_level = "auto-infer (beginner-safe)"

    normalized_goal = learning_goal.strip() if learning_goal else ""
    normalized_lesson_description = lesson_description.strip() if lesson_description else ""
    normalized_language = language.strip().lower() if language else ""
    if normalized_language not in {"english", "bengali", "hindi"}:
        normalized_language = "english"

    return {
        "course_title": course_title,
        "module_title": module_title,
        "lesson_title": lesson_title,
        "lesson_content": lesson_content,
        "lesson_description_context": normalized_lesson_description or "Not provided",
        "preferred_level_context": normalized_level,
        "learning_goal_context": normalized_goal or "Not provided",
        "language_context": normalized_language,
    }


async def generate_lesson_quiz(
    course_title: str,
    module_title: str,
    lesson_title: str,
    lesson_content: str,
    lesson_description: Optional[str] = None,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
) -> tuple[GeneratedLessonQuizSchema, LLMUsagePayload]:
    llm, llm_context = get_llm_client()

    prompt = ChatPromptTemplate.from_messages([
        ("system", LESSON_QUIZ_SYSTEM_PROMPT),
        ("user", f"{LESSON_QUIZ_USER_PROMPT}\n\n{LESSON_QUIZ_JSON_RULES}"),
    ])
    chain = prompt | llm

    prompt_inputs = build_lesson_quiz_prompt_inputs(
        course_title=course_title,
        module_title=module_title,
        lesson_title=lesson_title,
        lesson_content=lesson_content,
        lesson_description=lesson_description,
        learning_goal=learning_goal,
        preferred_level=preferred_level,
        language=language,
    )

    usage_callback = UsageMetadataCallbackHandler()
    result = await chain.ainvoke(prompt_inputs, config={"callbacks": [usage_callback]})
    parsed = parse_pydantic_from_response(result, GeneratedLessonQuizSchema)

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=result,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return parsed, usage
