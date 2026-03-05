from __future__ import annotations

from typing import Optional

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_json import parse_pydantic_from_response
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload
from app.schemas.course import GeneratedCourseSchema

COURSE_SYSTEM_PROMPT = """You are an expert curriculum designer and AI tutor with deep knowledge across all subjects.

Create a comprehensive, well-structured course syllabus that:

1. **Course Title**: Make it clear, engaging, and descriptive
   - Avoid generic titles
   - Include skill level if relevant (Beginner, Intermediate, Advanced)
   - Example: "Python for Data Science: From Zero to Hero" not just "Python Course"

2. **Course Description**: Write 2-5 sentences that:
   - Explain what the learner will master
   - Highlight practical outcomes and real-world applications
   - Create excitement about the learning journey

3. **Module Structure**: Create 4-7 logical modules that:
   - Follow a natural learning progression (basics → intermediate → advanced)
   - Each module focuses on one major concept or skill area
   - Build upon previous modules
   - Have clear, descriptive titles

4. **Lesson Structure**: Each module should have 3-7 lessons that:
   - Break down the module topic into digestible chunks
   - Progress from foundational to complex within the module
   - Have specific, actionable titles ("Understanding Variables" not "Introduction")
   - Cover one clear concept per lesson
   - Include a concise lesson description (1-3 sentences) describing exact coverage and outcomes

Guidelines:
- Total course should have 30-60 lessons across all modules
- Ensure smooth progression: each lesson builds on previous knowledge
- Balance theory with practical application
- For technical topics: Include fundamentals, practical skills, and advanced concepts
- For non-technical topics: Include history/context, core principles, and applications
- Each lesson MUST include a 1-3 sentence description that clearly defines exact scope and expected outcome
- If preferred level is provided, tune depth and progression accordingly
- If learning goal is provided, align modules and lessons to that goal
- Generate title, description, module titles, lesson titles, and lesson descriptions in the selected output language
- Keep unavoidable technical terms and proper nouns as-is when translation would be unclear"""

COURSE_USER_PROMPT = """Topic: {topic}
Preferred Level: {preferred_level_context}
Learning Goal: {learning_goal_context}
Output Language: {language_context}

Create a complete course syllabus following all guidelines above. Ensure the course is comprehensive enough to take a complete beginner to competency in this topic."""

COURSE_OPENAI_COMPAT_JSON_RULES = """
Output format requirements:
- Return ONLY valid JSON.
- Do NOT use markdown code fences.
- Do NOT add any text before or after the JSON.
- JSON shape:
  {
    "title": "string",
    "description": "string",
    "modules": [
      {
        "title": "string",
        "order_index": 1,
        "lessons": [
          {"title": "string", "description": "string", "order_index": 1}
        ]
      }
    ]
  }
"""


def build_course_syllabus_prompt_inputs(
    topic: str,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, str]:
    normalized_level = preferred_level.strip().lower() if preferred_level else ""
    if normalized_level not in {"beginner", "intermediate", "advanced"}:
        normalized_level = "auto-infer (beginner-safe)"

    normalized_goal = learning_goal.strip() if learning_goal else ""
    normalized_language = language.strip().lower() if language else ""
    if normalized_language not in {"english", "bengali", "hindi"}:
        normalized_language = "english"

    return {
        "topic": topic,
        "preferred_level_context": normalized_level,
        "learning_goal_context": normalized_goal or "Not provided",
        "language_context": normalized_language,
    }


async def generate_course_syllabus(
    topic: str,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
) -> tuple[GeneratedCourseSchema, LLMUsagePayload]:
    llm, llm_context = get_llm_client()
    is_openai_compatible = llm_context.get("provider") == "openai-compatible"

    if is_openai_compatible:
        prompt = ChatPromptTemplate.from_messages([
            ("system", COURSE_SYSTEM_PROMPT),
            ("user", f"{COURSE_USER_PROMPT}\n\n{COURSE_OPENAI_COMPAT_JSON_RULES}"),
        ])
        chain = prompt | llm
    else:
        structured_llm = llm.with_structured_output(GeneratedCourseSchema, include_raw=True)
        prompt = ChatPromptTemplate.from_messages([
            ("system", COURSE_SYSTEM_PROMPT),
            ("user", COURSE_USER_PROMPT),
        ])
        chain = prompt | structured_llm

    prompt_inputs = build_course_syllabus_prompt_inputs(
        topic=topic,
        learning_goal=learning_goal,
        preferred_level=preferred_level,
        language=language,
    )

    usage_callback = UsageMetadataCallbackHandler()
    result = await chain.ainvoke(prompt_inputs, config={"callbacks": [usage_callback]})
    if is_openai_compatible:
        parsed = parse_pydantic_from_response(result, GeneratedCourseSchema)
        raw_for_usage = result
    else:
        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError("Failed to parse syllabus generation response")
        raw_for_usage = result.get("raw")

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=raw_for_usage,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return parsed, usage
