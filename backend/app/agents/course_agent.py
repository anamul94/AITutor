from __future__ import annotations

import re
from typing import Any, Optional

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_json import parse_pydantic_from_response
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload
from app.schemas.course import (
    CourseGenerationMetadata,
    GeneratedCourseSchema,
    LessonGenerationMetadata,
)

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
    "ebpf",
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

LANGUAGE_KEYWORDS = {
    "rust": "rust",
    "golang": "go",
    "go language": "go",
    "go": "go",
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "c++": "c++",
    "c#": "c#",
    "kotlin": "kotlin",
    "ruby": "ruby",
    "swift": "swift",
}

CONSTRAINT_MARKERS = (" with ", " using ", " in ", " on ", " for ")
KNOWN_DOMAINS = (
    "ebpf",
    "react",
    "kafka",
    "kubernetes",
    "distributed systems",
    "fastapi",
    "system design",
    "postgres",
    "observability",
    "terraform",
)

COURSE_SYSTEM_PROMPT = """You are an expert technical curriculum designer and AI tutor.

Your job is to design deep, work-relevant courses for technical learners exploring software, frontend/backend, cloud, DevOps, SRE, networking, security, data/tooling, systems programming, and adjacent technical domains.

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
   - Follow a strong progression from foundations to professional capability.
   - Broad topics must progress through fundamentals, internals, implementation, debugging, performance/tradeoffs, and production practice when the topic supports it.
   - Avoid tutorial-series sprawl. Do not build a shallow install -> hello world -> more demos sequence.

4. **Lesson Structure**
   - Each module should have 5-7 lessons.
   - Total course size should land between 30 and 56 lessons.
   - Every lesson must have a focused title and a 1-3 sentence description with exact scope, expected outcome, and artifact expectations where relevant.
   - Every lesson must include structured generation metadata.
   - Use varied lesson types. Introductory concept/history lessons must not be forced into hands-on labs. Implementation/debugging/production lessons must be concrete and realistic.

5. **Technical Depth**
   - Optimize for professional capability, not tutorial completion.
   - Include internals, tradeoffs, debugging, failure modes, performance, architecture, and production concerns where the topic supports them.
   - "Real-world examples" means work-relevant scenarios, not toy-only framing when richer examples exist.

Guidelines:
- This is a technical learning system, not a general education platform.
- Support beginners, intermediates, and advanced learners as topic-depth levels, not job-role levels.
- If preferred level is provided, tune depth and progression accordingly.
- If learning goal is provided, align modules and lessons directly to that goal.
- Respect the requested content style when shaping theory vs practical emphasis.
- If the course has an explicit implementation language or stack constraint, keep lessons and examples anchored to it unless a comparison lesson explicitly requires contrast.
- Generate title, description, module titles, lesson titles, lesson descriptions, and learner-facing metadata text in the selected output language.
- Keep unavoidable technical terms, code terms, API names, and proper nouns unchanged when translation would reduce clarity."""

COURSE_USER_PROMPT = """Topic: {topic}
Preferred Level: {preferred_level_context}
Learning Goal: {learning_goal_context}
Content Style: {content_style_context}
Output Language: {language_context}
Topic Fit Guidance: {topic_fit_context}
Topic Interpretation Summary: {topic_interpretation_summary}
Specialization Mode: {specialization_mode_context}
Primary Implementation Language: {primary_language_context}
Allowed Example Technologies: {allowed_example_technologies_context}
Example Guardrails: {example_guardrails_context}

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
    "generation_metadata": {{
      "normalized_domain": "string",
      "stack_focus": "string or null",
      "primary_implementation_language": "string or null",
      "allowed_example_technologies": ["string"],
      "specialization_mode": "domain_first or stack_constrained",
      "course_intent": "professional_capability",
      "technical_focus_summary": "string",
      "example_guardrails": "string"
    }},
    "modules": [
      {{
        "title": "string",
        "order_index": 1,
        "lessons": [
          {{
            "title": "string",
            "description": "string",
            "order_index": 1,
            "generation_metadata": {{
              "lesson_type": "history|motivation|concept|architecture|internals|implementation|lab|debugging|comparison|case_study|performance|production",
              "depth_stage": "foundation|internals|implementation|debugging|optimization|production|advanced",
              "requires_worked_example": true,
              "requires_try_it_yourself": false,
              "requires_common_mistakes": true,
              "stack_constraints": ["string"],
              "artifact_expectations": "string",
              "example_policy": "string"
            }}
          }}
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
    topic_interpretation: Optional[CourseGenerationMetadata] = None,
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

    effective_interpretation = topic_interpretation or interpret_topic_focus(topic=topic, learning_goal=learning_goal)

    return {
        "topic": topic,
        "preferred_level_context": normalized_level,
        "learning_goal_context": normalized_goal or "Not provided",
        "content_style_context": normalized_content_style,
        "language_context": normalized_language,
        "topic_fit_context": topic_fit_context or "Strong technical match. Keep the course technical and work-relevant.",
        "topic_interpretation_summary": effective_interpretation.technical_focus_summary,
        "specialization_mode_context": effective_interpretation.specialization_mode,
        "primary_language_context": effective_interpretation.primary_implementation_language or "Not constrained",
        "allowed_example_technologies_context": ", ".join(effective_interpretation.allowed_example_technologies)
        or "Use topic-relevant technologies only",
        "example_guardrails_context": effective_interpretation.example_guardrails,
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
                "practical outcomes, meaningful depth, and production-aware progression."
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


def interpret_topic_focus(topic: str, learning_goal: Optional[str] = None) -> CourseGenerationMetadata:
    normalized_topic = " ".join(topic.strip().split())
    topic_lower = normalized_topic.lower()
    learning_goal_lower = (learning_goal or "").strip().lower()
    combined = " ".join(part for part in (topic_lower, learning_goal_lower) if part)

    normalized_domain = _detect_primary_domain(topic_lower) or normalized_topic.lower()
    primary_language = _detect_primary_language(combined)
    stack_focus = _detect_stack_focus(normalized_topic)
    specialization_mode = "stack_constrained" if primary_language or stack_focus else "domain_first"

    allowed_example_technologies: list[str] = []
    if normalized_domain:
        allowed_example_technologies.append(normalized_domain)
    if stack_focus and stack_focus.lower() not in allowed_example_technologies:
        allowed_example_technologies.append(stack_focus.lower())
    if primary_language and primary_language not in allowed_example_technologies:
        allowed_example_technologies.append(primary_language)

    if specialization_mode == "stack_constrained":
        technical_focus_summary = (
            f"Treat `{normalized_topic}` as a constrained technical path. Keep the course anchored to "
            f"{stack_focus or normalized_domain}, and preserve the requested implementation context."
        )
        example_guardrails = (
            f"Primary examples must stay anchored to {primary_language or stack_focus or normalized_domain}. "
            "Only use other stacks when a lesson is explicitly marked as a comparison."
        )
    else:
        technical_focus_summary = (
            f"Treat `{normalized_topic}` as a broad technical domain. Start with foundations and internals, "
            "then progress into implementation, debugging, performance, tradeoffs, and production capability."
        )
        example_guardrails = (
            "Use topic-relevant technologies only. Do not commit too early to one stack unless the syllabus "
            "explicitly introduces a specialization path."
        )

    return CourseGenerationMetadata(
        normalized_domain=normalized_domain or normalized_topic.lower(),
        stack_focus=stack_focus,
        primary_implementation_language=primary_language,
        allowed_example_technologies=allowed_example_technologies,
        specialization_mode=specialization_mode,
        course_intent="professional_capability",
        technical_focus_summary=technical_focus_summary,
        example_guardrails=example_guardrails,
    )


def get_effective_course_generation_metadata(
    topic: str,
    learning_goal: Optional[str] = None,
    generation_metadata: Optional[dict[str, Any]] = None,
) -> CourseGenerationMetadata:
    if generation_metadata:
        return CourseGenerationMetadata.model_validate(generation_metadata)
    return interpret_topic_focus(topic=topic, learning_goal=learning_goal)


def get_effective_lesson_generation_metadata(
    lesson_title: str,
    lesson_description: Optional[str] = None,
    course_generation_metadata: Optional[CourseGenerationMetadata | dict[str, Any]] = None,
    generation_metadata: Optional[dict[str, Any]] = None,
) -> LessonGenerationMetadata:
    if generation_metadata:
        return LessonGenerationMetadata.model_validate(generation_metadata)

    metadata = (
        CourseGenerationMetadata.model_validate(course_generation_metadata)
        if isinstance(course_generation_metadata, dict)
        else course_generation_metadata
    )
    stack_constraints = list(metadata.allowed_example_technologies) if metadata else []
    lesson_type = _infer_lesson_type(lesson_title, lesson_description)
    depth_stage = _infer_depth_stage(lesson_type)
    requires_worked_example = lesson_type not in {"history", "motivation", "concept"}
    requires_try_it_yourself = lesson_type in {"implementation", "lab", "debugging", "production"}
    requires_common_mistakes = lesson_type not in {"history", "motivation"}

    if lesson_type in {"history", "motivation", "concept"}:
        artifact_expectations = "Reasoning-focused explanation, technical context, and concrete system examples when helpful."
        example_policy = "Examples may be illustrative but do not force hands-on tasks when they are not relevant."
    elif lesson_type in {"comparison", "architecture", "internals", "performance"}:
        artifact_expectations = "Comparisons, tradeoff tables, architectural reasoning, and realistic scenario analysis."
        example_policy = "Use constrained stack examples when helpful, but contrast options explicitly."
    else:
        artifact_expectations = "Concrete code, commands, configs, debugging steps, or production validation workflow."
        example_policy = "Primary examples must stay inside the course stack constraints and remain work-relevant."

    return LessonGenerationMetadata(
        lesson_type=lesson_type,
        depth_stage=depth_stage,
        requires_worked_example=requires_worked_example,
        requires_try_it_yourself=requires_try_it_yourself,
        requires_common_mistakes=requires_common_mistakes,
        stack_constraints=stack_constraints,
        artifact_expectations=artifact_expectations,
        example_policy=example_policy,
    )


def _detect_primary_domain(topic_lower: str) -> str:
    for domain in sorted(KNOWN_DOMAINS + TECHNICAL_TOPIC_KEYWORDS, key=len, reverse=True):
        if _contains_keyword(topic_lower, domain):
            return domain
    return topic_lower.strip()


def _detect_primary_language(text: str) -> Optional[str]:
    for keyword, normalized in sorted(LANGUAGE_KEYWORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_keyword(text, keyword):
            return normalized
    return None


def _detect_stack_focus(topic: str) -> Optional[str]:
    normalized = f" {topic.lower()} "
    for marker in CONSTRAINT_MARKERS:
        if marker in normalized:
            _, tail = normalized.split(marker, 1)
            cleaned = tail.strip(" .,:;")
            if cleaned and (
                _detect_primary_language(cleaned) is not None
                or any(_contains_keyword(cleaned, domain) for domain in KNOWN_DOMAINS)
            ):
                return cleaned
    return None


def _infer_lesson_type(lesson_title: str, lesson_description: Optional[str] = None) -> str:
    combined = " ".join(part for part in (lesson_title, lesson_description or "") if part).lower()
    if any(keyword in combined for keyword in ("history", "evolution", "origins")):
        return "history"
    if any(keyword in combined for keyword in ("why", "benefit", "motivation", "use case", "when to use")):
        return "motivation"
    if any(keyword in combined for keyword in ("architecture", "design", "internals", "how it works")):
        if "internals" in combined:
            return "internals"
        return "architecture"
    if any(keyword in combined for keyword in ("compare", "comparison", "versus", "vs")):
        return "comparison"
    if any(keyword in combined for keyword in ("debug", "troubleshoot", "pitfall", "failure")):
        return "debugging"
    if any(keyword in combined for keyword in ("performance", "latency", "throughput", "optimiz")):
        return "performance"
    if any(keyword in combined for keyword in ("production", "deploy", "operat", "observe", "reliability")):
        return "production"
    if any(keyword in combined for keyword in ("lab", "build", "implement", "hands-on", "project", "code")):
        return "implementation"
    return "concept"


def _infer_depth_stage(lesson_type: str) -> str:
    return {
        "history": "foundation",
        "motivation": "foundation",
        "concept": "foundation",
        "architecture": "internals",
        "internals": "internals",
        "implementation": "implementation",
        "lab": "implementation",
        "debugging": "debugging",
        "comparison": "optimization",
        "case_study": "production",
        "performance": "optimization",
        "production": "production",
    }.get(lesson_type, "foundation")


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
    topic_interpretation = interpret_topic_focus(topic=topic, learning_goal=learning_goal)

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
        topic_interpretation=topic_interpretation,
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
