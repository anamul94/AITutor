from __future__ import annotations

from typing import Any, Optional

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate

from app.agents.course_agent import (
    get_effective_course_generation_metadata,
    get_effective_lesson_generation_metadata,
)
from app.core.llm_json import parse_pydantic_from_response
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload
from app.schemas.course import (
    CourseGenerationMetadata,
    GeneratedLessonQuizSchema,
    LessonGenerationMetadata,
)

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
11. Respect course stack constraints. If the course is constrained to Rust or another implementation path, quiz scenarios must stay anchored there unless the lesson is explicitly comparative.
12. Concept/history/motivation lessons should bias toward reasoning, internals, and tradeoffs instead of fake hands-on trivia.
13. Implementation/debugging/production lessons should include practical reasoning about code behavior, troubleshooting, or realistic engineering decisions.
"""

LESSON_QUIZ_USER_PROMPT = """Course: {course_title}
Module: {module_title}
Lesson: {lesson_title}
Lesson Description Scope: {lesson_description_context}
Preferred Level: {preferred_level_context}
Learning Goal: {learning_goal_context}
Output Language: {language_context}
Primary Implementation Language: {primary_language_context}
Allowed Example Technologies: {allowed_example_technologies_context}
Lesson Type: {lesson_type_context}
Depth Stage: {depth_stage_context}
Stack Constraints: {stack_constraints_context}
Example Policy: {example_policy_context}

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
    topic: Optional[str] = None,
    course_generation_metadata: Optional[CourseGenerationMetadata | dict[str, Any]] = None,
    lesson_generation_metadata: Optional[LessonGenerationMetadata | dict[str, Any]] = None,
) -> dict[str, str]:
    normalized_level = preferred_level.strip().lower() if preferred_level else ""
    if normalized_level not in {"beginner", "intermediate", "advanced"}:
        normalized_level = "auto-infer (beginner-safe)"

    normalized_goal = learning_goal.strip() if learning_goal else ""
    normalized_lesson_description = lesson_description.strip() if lesson_description else ""
    normalized_language = language.strip().lower() if language else ""
    if normalized_language not in {"english", "bengali", "hindi"}:
        normalized_language = "english"

    effective_course_metadata = get_effective_course_generation_metadata(
        topic=topic or course_title,
        learning_goal=learning_goal,
        generation_metadata=course_generation_metadata if isinstance(course_generation_metadata, dict) else (
            course_generation_metadata.model_dump() if course_generation_metadata else None
        ),
    )
    effective_lesson_metadata = get_effective_lesson_generation_metadata(
        lesson_title=lesson_title,
        lesson_description=lesson_description,
        course_generation_metadata=effective_course_metadata,
        generation_metadata=lesson_generation_metadata if isinstance(lesson_generation_metadata, dict) else (
            lesson_generation_metadata.model_dump() if lesson_generation_metadata else None
        ),
    )

    return {
        "course_title": course_title,
        "module_title": module_title,
        "lesson_title": lesson_title,
        "lesson_content": lesson_content,
        "lesson_description_context": normalized_lesson_description or "Not provided",
        "preferred_level_context": normalized_level,
        "learning_goal_context": normalized_goal or "Not provided",
        "language_context": normalized_language,
        "primary_language_context": effective_course_metadata.primary_implementation_language or "Not constrained",
        "allowed_example_technologies_context": ", ".join(effective_course_metadata.allowed_example_technologies)
        or "Use topic-relevant technologies only",
        "lesson_type_context": effective_lesson_metadata.lesson_type,
        "depth_stage_context": effective_lesson_metadata.depth_stage,
        "stack_constraints_context": ", ".join(effective_lesson_metadata.stack_constraints) or "Follow the course topic naturally",
        "example_policy_context": effective_lesson_metadata.example_policy,
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
    topic: Optional[str] = None,
    course_generation_metadata: Optional[CourseGenerationMetadata | dict[str, Any]] = None,
    lesson_generation_metadata: Optional[LessonGenerationMetadata | dict[str, Any]] = None,
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
        topic=topic,
        course_generation_metadata=course_generation_metadata,
        lesson_generation_metadata=lesson_generation_metadata,
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
