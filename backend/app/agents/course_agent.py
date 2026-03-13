from __future__ import annotations

import re
from typing import Any, Optional

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_json import parse_pydantic_from_response
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload
from app.schemas.course import GeneratedCourseSchema

TOPIC_WARNING_MESSAGE = (
    "This system is optimized for technical learning. "
    "Your topic looks outside that focus, so the generated course is a best-effort interpretation."
)

TECHNICAL_TOPIC_KEYWORDS = (
    "algorithm",
    "api",
    "architecture",
    "aws",
    "azure",
    "backend",
    "bash",
    "c++",
    "c#",
    "ci/cd",
    "cloud",
    "computer",
    "container",
    "css",
    "cybersecurity",
    "data engineering",
    "database",
    "debug",
    "deployment",
    "devops",
    "django",
    "distributed systems",
    "docker",
    "fastapi",
    "flask",
    "frontend",
    "gcp",
    "git",
    "github",
    "go language",
    "golang",
    "grafana",
    "graphql",
    "html",
    "http",
    "infra",
    "infrastructure",
    "java",
    "javascript",
    "kafka",
    "kotlin",
    "kubernetes",
    "k8s",
    "linux",
    "llm",
    "machine learning",
    "microservice",
    "monitoring",
    "mysql",
    "network",
    "networking",
    "next.js",
    "nginx",
    "node",
    "observability",
    "postgres",
    "prometheus",
    "python",
    "react",
    "redis",
    "rest api",
    "ruby",
    "rust",
    "security",
    "shell",
    "site reliability",
    "sre",
    "sql",
    "swift",
    "system design",
    "tcp",
    "terraform",
    "testing",
    "typescript",
    "udp",
)

NON_TECHNICAL_TOPIC_KEYWORDS = (
    "art history",
    "baking",
    "biology",
    "cooking",
    "creative writing",
    "dance",
    "drawing",
    "fashion",
    "fitness",
    "history of rome",
    "literature",
    "meditation",
    "music theory",
    "nutrition",
    "painting",
    "philosophy",
    "poetry",
    "psychology",
    "public speaking",
    "roman empire",
    "sociology",
    "yoga",
)

COURSE_SYSTEM_PROMPT = """You are an expert technical curriculum designer and AI tutor.

Your job is to design deep, work-relevant courses for technical learners exploring software, frontend/backend, cloud, DevOps, SRE, networking, security, data/tooling, and adjacent technical domains.

Create a comprehensive, well-structured technical course syllabus that:

1. **Course Title**
   - Make it clear, specific, and credible for a technical learner.
   - Avoid generic titles.
   - Include level only when useful.

2. **Course Description**
   - Write 2-5 sentences describing what the learner will be able to do.
   - Emphasize practical outcomes, real engineering context, and capability growth.
   - If the course is advanced, mention internals, tradeoffs, or production concerns where relevant.

3. **Module Structure**
   - Create 6-8 logical modules.
   - Follow a strong progression: foundations -> applied usage -> deeper concepts -> professional capability.
   - Each module should represent a meaningful skill milestone, not filler.

4. **Lesson Structure**
   - Each module should have 5-7 lessons.
   - Total course size should land between 30 and 56 lessons.
   - Every lesson must have a focused title and a 1-3 sentence description with exact scope and expected outcome.
   - Avoid tutorial-series sprawl. Prefer capability-building progression over endless syntax walkthroughs.

Guidelines:
- This is a technical learning system, not a general education platform.
- Support beginners, intermediates, and advanced learners as topic-depth levels, not job-role levels.
- A beginner course may start from first principles of the technical topic, but it should still feel like technical learning.
- Intermediate courses should move faster through basics and build practical competence sooner.
- Advanced courses should emphasize internals, tradeoffs, performance, architecture, failure modes, debugging, and production reality.
- "Real-world examples" means work-relevant scenarios, not toy-only or hello-world-only examples when richer examples exist.
- If preferred level is provided, tune depth and progression accordingly.
- If learning goal is provided, align modules and lessons directly to that goal.
- Respect the requested content style when shaping theory vs practical emphasis.
- Generate title, description, module titles, lesson titles, and lesson descriptions in the selected output language.
- Keep unavoidable technical terms, code terms, API names, and proper nouns unchanged when translation would reduce clarity."""

COURSE_USER_PROMPT = """Topic: {topic}
Preferred Level: {preferred_level_context}
Learning Goal: {learning_goal_context}
Content Style: {content_style_context}
Output Language: {language_context}
Topic Fit Guidance: {topic_fit_context}

Create a complete technical course syllabus following all guidelines above.
The syllabus should help a learner grow from their current depth toward professional capability in this topic without getting trapped in shallow tutorial-only sequencing."""

COURSE_OPENAI_COMPAT_JSON_RULES = """
Output format requirements:
- Return ONLY valid JSON.
- Do NOT use markdown code fences.
- Do NOT add any text before or after the JSON.
- JSON shape:
  {{
    "title": "string",
    "description": "string",
    "modules": [
      {{
        "title": "string",
        "order_index": 1,
        "lessons": [
          {{"title": "string", "description": "string", "order_index": 1}}
        ]
      }}
    ]
  }}
"""


def build_course_syllabus_prompt_inputs(
    topic: str,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
    content_style: Optional[str] = None,
    topic_fit_context: Optional[str] = None,
) -> dict[str, str]:
    normalized_level = preferred_level.strip().lower() if preferred_level else ""
    if normalized_level not in {"beginner", "intermediate", "advanced"}:
        normalized_level = "auto-infer (beginner-safe)"

    normalized_goal = learning_goal.strip() if learning_goal else ""
    normalized_language = language.strip().lower() if language else ""
    if normalized_language not in {"english", "bengali", "hindi"}:
        normalized_language = "english"
    normalized_content_style = content_style.strip().lower() if content_style else ""
    if normalized_content_style not in {"conceptual", "balanced", "practical"}:
        normalized_content_style = "balanced"

    return {
        "topic": topic,
        "preferred_level_context": normalized_level,
        "learning_goal_context": normalized_goal or "Not provided",
        "content_style_context": normalized_content_style,
        "language_context": normalized_language,
        "topic_fit_context": topic_fit_context or "Strong technical match. Keep the course technical and work-relevant.",
    }


def assess_topic_fit(topic: str, learning_goal: Optional[str] = None) -> dict[str, Any]:
    combined = " ".join(part for part in (topic, learning_goal or "") if part).lower()
    has_technical_signal = any(_contains_keyword(combined, keyword) for keyword in TECHNICAL_TOPIC_KEYWORDS)
    has_non_technical_signal = any(
        _contains_keyword(combined, keyword) for keyword in NON_TECHNICAL_TOPIC_KEYWORDS
    )

    if has_technical_signal:
        return {
            "fit": "technical",
            "warnings": [],
            "prompt_guidance": (
                "Strong technical match. Design a rigorous technical course with work-relevant examples, "
                "practical outcomes, and meaningful depth."
            ),
        }

    if has_non_technical_signal:
        return {
            "fit": "weak",
            "warnings": [TOPIC_WARNING_MESSAGE],
            "prompt_guidance": (
                "This topic appears outside the platform's technical focus. Generate a best-effort structured course, "
                "stay honest about scope, and avoid inventing false technical relevance."
            ),
        }

    return {
        "fit": "adjacent",
        "warnings": [],
        "prompt_guidance": (
            "No strong topic-fit signal was detected. Bias toward a technical, analytical, work-relevant interpretation "
            "if the topic reasonably supports it."
        ),
    }


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    if re.search(r"[^a-z0-9\s]", keyword):
        return keyword in text
    pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


async def generate_course_syllabus(
    topic: str,
    learning_goal: Optional[str] = None,
    preferred_level: Optional[str] = None,
    language: Optional[str] = None,
    content_style: Optional[str] = None,
) -> tuple[GeneratedCourseSchema, list[str], LLMUsagePayload]:
    llm, llm_context = get_llm_client()
    is_openai_compatible = llm_context.get("provider") == "openai-compatible"
    topic_fit = assess_topic_fit(topic=topic, learning_goal=learning_goal)

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
        content_style=content_style,
        topic_fit_context=str(topic_fit["prompt_guidance"]),
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
    return parsed, list(topic_fit["warnings"]), usage
