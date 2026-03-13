from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.core.llm_json import parse_pydantic_from_response, response_content_to_text
from app.core.llm_providers import get_llm_client
from app.core.llm_usage import LLMUsagePayload, build_usage_payload

LEARN_ANALYSIS_SYSTEM_PROMPT = """You are an expert DSA teaching analyst. Your job is to deeply read the conversation and the learner's latest message to diagnose where they are and what the teacher must do next.

Key signals to read carefully:
1. Did the learner answer the last checkpoint question? Was the answer correct, partially correct, or wrong?
2. Is the learner confused, stuck, or asking for re-explanation?
3. Has the learner demonstrated real understanding through their own words, code, or reasoning?
4. What is the exact concept gap or misconception — not a vague summary, be specific.
5. Should a worked trace-through example be shown? (yes when teaching a new concept for the first time, when student is stuck, or when student gave wrong answer)

Rules:
- comprehension_verified = true ONLY if the learner's message shows they genuinely understood the last concept with their own reasoning or correct answer.
- stuck_signal = true if learner says "I don't understand", "I'm confused", "lost", or asks the same question again, or gives a clearly wrong answer with no reasoning.
- example_needed = true when teaching a new concept chunk for the first time, when student is stuck, or when student answered incorrectly.
- next_action options:
  - assess_baseline: opening turn or prior knowledge is unknown — check what they already know.
  - explain_concept: introduce and build a new concept chunk from intuition to mechanics.
  - worked_example: student needs to see a full step-by-step trace-through with a concrete example.
  - correct_misconception: student holds a specific wrong belief — address it by naming the misconception directly.
  - bridge_prerequisite: learner lacks a required prerequisite — teach that first.
  - give_practice: learner understood well — give them a task to attempt themselves.
  - verify_understanding: ask a targeted question to confirm comprehension before moving forward.
  - reflection: learner requested session summary or said they are done.
- Return only JSON for the schema.
"""

LEARN_ANALYSIS_USER_PROMPT = """Mode: learn_topic
Topic: {topic}
Learning Track Context:
{problem_statement}

Learner Prior Knowledge:
{prior_knowledge}

Recent Conversation:
{history_excerpt}

Latest Learner Message:
{last_user_message}
"""

LEARN_ANALYSIS_OPENAI_JSON_RULES = """
Output format requirements:
- Return ONLY valid JSON.
- Do NOT use markdown code fences.
- Do NOT add any text before or after the JSON.
- JSON shape:
  {{
    "next_action": "assess_baseline|explain_concept|worked_example|correct_misconception|bridge_prerequisite|give_practice|verify_understanding|reflection",
    "learner_stage": "understanding|application|debugging|complexity|reflection",
    "teaching_depth": "light|medium|deep",
    "comprehension_verified": false,
    "example_needed": true,
    "stuck_signal": false,
    "request_reflection": false,
    "diagnosis": "string — specific and thorough: what exactly does the learner understand or not understand, and why",
    "concept_focus": "string — the exact concept chunk being taught this turn",
    "prerequisite_focus": "string — prerequisite gap if any, else 'none'",
    "observed_mistakes": ["string"],
    "likely_weak_areas": [
      {{"area": "string", "reason": "string", "severity": "low|medium|high"}}
    ]
  }}
"""

LEARN_RESPONSE_SYSTEM_PROMPT = """You are an expert DSA teacher who teaches by doing — like a patient senior engineer mentoring a junior colleague.

Core rules (always apply):
1. Acknowledge what the learner said first. Validate correct parts; name and correct wrong parts specifically. Never skip this.
2. Intuition before mechanics. Always explain the "why" before the "how".
3. Use concrete language. Code snippets, pseudocode, array-state annotations ([2,5,1,8] → left=0, right=3) wherever they help.
4. When correcting a misconception: name it explicitly — "Your thinking assumes X, but actually Y because Z."
5. When stuck_signal is true: strip the problem to one step, use a smaller example, ask what specific part broke.
6. Checkpoint questions must require the learner to apply or recall something concrete — never "do you understand?"
7. When a concept has visual structure (pointer movement, tree traversal, graph BFS/DFS), include a small focused Mermaid diagram in a ```mermaid block.
8. The format of your response changes per teaching action — follow the format instructions exactly.
9. Respond in the language specified by "Output language". Keep technical terms (variable names, Big-O notation, algorithm names, code) in English regardless of language.
"""

# Per-action response formats injected into the user prompt.
# Each action gets a different structure so responses don't feel like a template.
RESPONSE_FORMAT_BY_ACTION = {
    "assess_baseline": """\
Write conversationally — no section headers.
- Open with 1-2 sentences setting context for what you will cover.
- Ask 2-3 targeted diagnostic questions to map what the learner already knows.
  Cover: definition/intuition, a use case, and one common pitfall or edge case.
- Keep it short. No explanations yet — you are listening, not teaching.""",

    "explain_concept": """\
### [Name the concept as the heading — not "Core Concept"]
Intuition first: the "why". Then mechanics. Use code/pseudocode/annotations.
If prerequisite_focus is not "none", open with a brief prerequisite bridge first.

### Trace Through: [small example title]
Step-by-step on a 4-5 element example. Show exact data structure state at EVERY step.
Label each step (Step 1, Step 2 …). Do not skip steps.

**Try this:** One small, achievable practice task directly applying what was just explained.

**Check:** One specific targeted question — about a concrete step, state, or decision in the example above.""",

    "worked_example": """\
(1–2 sentence acknowledgement inline, no header — validate or gently correct first)

### Walk-through: [descriptive title]
Full step-by-step trace on a concrete example. Show every state change. Annotate clearly.
Use a Mermaid diagram if the concept has visual structure.

**Now trace this yourself:** Give a slightly different input for the learner to trace on their own.
One sentence hint if helpful.""",

    "correct_misconception": """\
Open immediately with the correction (no header):
"Your current thinking is [restate their belief] — but actually [correct model], because [reason]."

### The right way to think about it
Re-explain from the correct angle. One focused example that breaks the misconception.

**Quick check:** One question that can only be answered correctly if the misconception is gone.""",

    "bridge_prerequisite": """\
### Quick prerequisite: [prereq name]
Tight explanation — just enough to unlock the main concept. One small example if needed.

### Back to [main topic]
Explicit bridge: "Now that you understand X, here is how it connects to Y."

**Check:** One question confirming they got the prerequisite.""",

    "give_practice": """\
(1–2 sentence acknowledgement of their progress — no header)

### Your turn: [short task title]
One concrete practice problem or coding task, stated clearly.
Include example input and expected output.
Do not give the solution or heavy hints upfront.

💡 Ask me for a hint if you get stuck.""",

    "verify_understanding": """\
(1 sentence acknowledgement — inline, no header)

**Check:** [One specific, targeted question — must require applying or recalling something concrete from this session. Not "do you understand?"]""",

    "reflection": """\
### What you've built
List the specific concepts the learner demonstrated understanding of. Be precise.

### Where to sharpen
List specific weak areas with brief evidence from the conversation. Be direct and honest.

### Next 3 steps
Three ordered, concrete practice steps. Each = a specific problem type or exercise — not generic advice.""",
}

LEARN_RESPONSE_USER_PROMPT = """Topic: {topic}
Output language: {language}
Teaching action: {next_action}
Learner stage: {learner_stage}
Teaching depth: {teaching_depth}
Comprehension verified: {comprehension_verified}
Student is stuck: {stuck_signal}
Show worked example: {example_needed}
Diagnosis: {diagnosis}
Concept focus: {concept_focus}
Prerequisite gap: {prerequisite_focus}
Observed mistakes: {observed_mistakes}

Learner Prior Knowledge:
{prior_knowledge}

Latest Learner Message:
{last_user_message}

--- RESPONSE FORMAT FOR THIS TURN ({next_action}) ---
{response_format}
"""

LEARN_REFLECTION_SYSTEM_PROMPT = """You are a DSA learning reflection coach.

Create a precise, honest reflection:
1. List specific concepts the learner demonstrated understanding of.
2. List specific concepts or areas that are still weak or uncertain, with evidence from the conversation.
3. Give a concrete, ordered 3-step next practice plan — specific problems or exercises, not generic advice.
"""

LEARN_REFLECTION_USER_PROMPT = """Topic: {topic}
Diagnosis: {diagnosis}
Observed mistakes: {observed_mistakes}
Weak areas: {weak_areas}
Learner Prior Knowledge:
{prior_knowledge}
Latest Learner Message:
{last_user_message}

Use this format:
### Progress Summary
(List specific concepts understood. Be precise — "understands two-pointer movement" not just "understands arrays".)

### Gaps To Fix
(List specific weak areas with brief evidence from the conversation. Be direct.)

### Next Practice Plan
(3 ordered, concrete steps. Each step = a specific type of problem or exercise to do next. No vague advice.)
"""


class LearnWeakAreaSignalSchema(BaseModel):
    area: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=5, max_length=500)
    severity: Literal["low", "medium", "high"] = "medium"


class LearnTurnAnalysisSchema(BaseModel):
    next_action: Literal[
        "assess_baseline",
        "explain_concept",
        "worked_example",
        "correct_misconception",
        "bridge_prerequisite",
        "give_practice",
        "verify_understanding",
        "reflection",
    ] = "explain_concept"
    learner_stage: Literal["understanding", "application", "debugging", "complexity", "reflection"] = "understanding"
    teaching_depth: Literal["light", "medium", "deep"] = "medium"
    comprehension_verified: bool = False
    example_needed: bool = True
    stuck_signal: bool = False
    request_reflection: bool = False
    diagnosis: str = Field(min_length=5, max_length=2000)
    concept_focus: str = Field(min_length=2, max_length=120)
    prerequisite_focus: str = Field(default="none", max_length=120)
    observed_mistakes: list[str] = Field(default_factory=list, max_length=6)
    likely_weak_areas: list[LearnWeakAreaSignalSchema] = Field(default_factory=list, max_length=6)


class DSALearnState(TypedDict, total=False):
    topic: str
    language: str
    problem_statement: str
    prior_knowledge: str
    history_excerpt: str
    last_user_message: str
    detected_mode: str
    analysis: dict[str, Any]
    assistant_message: str
    weak_area_signals: list[dict[str, str]]
    analysis_usage: LLMUsagePayload
    response_usage: LLMUsagePayload


def build_dsa_learn_prompt_inputs(
    *,
    topic: str,
    language: str = "english",
    problem_statement: str,
    prior_knowledge: str | None,
    history_excerpt: str | None,
    last_user_message: str,
) -> dict[str, str]:
    normalized_lang = (language or "english").strip().lower()
    if normalized_lang not in {"english", "bengali", "hindi"}:
        normalized_lang = "english"
    return {
        "topic": topic.strip().lower(),
        "language": normalized_lang,
        "problem_statement": problem_statement.strip(),
        "prior_knowledge": (prior_knowledge or "").strip() or "Not provided",
        "history_excerpt": ((history_excerpt or "").strip() or "No prior turns yet.")[-8000:],
        "last_user_message": last_user_message.strip(),
    }


def _detect_mode_node(state: DSALearnState) -> dict[str, str]:
    message = (state.get("last_user_message") or "").lower()
    reflection_markers = ("i finished", "done", "reflect", "review")
    detected_mode = "reflection" if any(marker in message for marker in reflection_markers) else "coach"
    return {"detected_mode": detected_mode}


async def _analyze_turn_node(state: DSALearnState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    is_openai_compatible = llm_context.get("provider") == "openai-compatible"
    usage_callback = UsageMetadataCallbackHandler()

    if is_openai_compatible:
        prompt = ChatPromptTemplate.from_messages([
            ("system", LEARN_ANALYSIS_SYSTEM_PROMPT),
            ("user", f"{LEARN_ANALYSIS_USER_PROMPT}\n\n{LEARN_ANALYSIS_OPENAI_JSON_RULES}"),
        ])
        chain = prompt | llm
        raw_result = await chain.ainvoke(state, config={"callbacks": [usage_callback]})
        analysis = parse_pydantic_from_response(raw_result, LearnTurnAnalysisSchema)
        raw_for_usage = raw_result
    else:
        structured_llm = llm.with_structured_output(LearnTurnAnalysisSchema, include_raw=True)
        prompt = ChatPromptTemplate.from_messages([
            ("system", LEARN_ANALYSIS_SYSTEM_PROMPT),
            ("user", LEARN_ANALYSIS_USER_PROMPT),
        ])
        chain = prompt | structured_llm
        result = await chain.ainvoke(state, config={"callbacks": [usage_callback]})
        analysis = result.get("parsed")
        raw_for_usage = result.get("raw")
        if analysis is None:
            parsing_error = result.get("parsing_error")
            logger.warning(
                "Bedrock structured output failed to parse learn analysis (error=%s). Falling back to JSON parse.",
                parsing_error,
            )
            analysis = parse_pydantic_from_response(raw_for_usage, LearnTurnAnalysisSchema)

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=raw_for_usage,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return {"analysis": analysis.model_dump(), "analysis_usage": usage}


def _route_after_analysis(state: DSALearnState) -> str:
    analysis = state.get("analysis") or {}
    if state.get("detected_mode") == "reflection" or bool(analysis.get("request_reflection")):
        return "reflection_response"
    return "learn_response"


def _analysis_to_strings(analysis: LearnTurnAnalysisSchema) -> dict[str, str]:
    mistakes = analysis.observed_mistakes or ["None explicitly identified yet."]
    weak_areas = [f"{item.area} ({item.severity})" for item in analysis.likely_weak_areas]
    return {
        "observed_mistakes": "; ".join(mistakes),
        "weak_areas": "; ".join(weak_areas) if weak_areas else "No clear weak area signal yet.",
    }


async def _learn_response_node(state: DSALearnState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    analysis = LearnTurnAnalysisSchema.model_validate(state.get("analysis") or {})
    display = _analysis_to_strings(analysis)

    prompt = ChatPromptTemplate.from_messages([
        ("system", LEARN_RESPONSE_SYSTEM_PROMPT),
        ("user", LEARN_RESPONSE_USER_PROMPT),
    ])
    chain = prompt | llm
    usage_callback = UsageMetadataCallbackHandler()
    response_format = RESPONSE_FORMAT_BY_ACTION.get(
        analysis.next_action,
        RESPONSE_FORMAT_BY_ACTION["explain_concept"],
    )
    raw_result = await chain.ainvoke(
        {
            **state,
            "next_action": analysis.next_action,
            "learner_stage": analysis.learner_stage,
            "teaching_depth": analysis.teaching_depth,
            "comprehension_verified": str(analysis.comprehension_verified),
            "example_needed": str(analysis.example_needed),
            "stuck_signal": str(analysis.stuck_signal),
            "diagnosis": analysis.diagnosis,
            "concept_focus": analysis.concept_focus,
            "prerequisite_focus": analysis.prerequisite_focus,
            "observed_mistakes": display["observed_mistakes"],
            "response_format": response_format,
            "language": state.get("language") or "english",
        },
        config={"callbacks": [usage_callback]},
    )
    assistant_message = response_content_to_text(getattr(raw_result, "content", raw_result)).strip()
    if not assistant_message:
        raise ValueError("Failed to generate DSA learn response")

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=raw_result,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return {
        "assistant_message": assistant_message,
        "weak_area_signals": [item.model_dump() for item in analysis.likely_weak_areas],
        "response_usage": usage,
    }


async def _reflection_response_node(state: DSALearnState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    analysis = LearnTurnAnalysisSchema.model_validate(state.get("analysis") or {})
    display = _analysis_to_strings(analysis)

    prompt = ChatPromptTemplate.from_messages([
        ("system", LEARN_REFLECTION_SYSTEM_PROMPT),
        ("user", LEARN_REFLECTION_USER_PROMPT),
    ])
    chain = prompt | llm
    usage_callback = UsageMetadataCallbackHandler()
    raw_result = await chain.ainvoke(
        {
            **state,
            "diagnosis": analysis.diagnosis,
            "observed_mistakes": display["observed_mistakes"],
            "weak_areas": display["weak_areas"],
        },
        config={"callbacks": [usage_callback]},
    )
    assistant_message = response_content_to_text(getattr(raw_result, "content", raw_result)).strip()
    if not assistant_message:
        raise ValueError("Failed to generate DSA learn reflection response")

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=raw_result,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return {
        "assistant_message": assistant_message,
        "weak_area_signals": [item.model_dump() for item in analysis.likely_weak_areas],
        "response_usage": usage,
    }


def _build_usage_totals(
    analysis_usage: dict[str, Any] | None,
    response_usage: dict[str, Any] | None,
) -> LLMUsagePayload:
    analysis_usage = analysis_usage or {}
    response_usage = response_usage or {}
    return {
        "input_tokens": int(analysis_usage.get("input_tokens", 0) or 0)
        + int(response_usage.get("input_tokens", 0) or 0),
        "output_tokens": int(analysis_usage.get("output_tokens", 0) or 0)
        + int(response_usage.get("output_tokens", 0) or 0),
        "total_tokens": int(analysis_usage.get("total_tokens", 0) or 0)
        + int(response_usage.get("total_tokens", 0) or 0),
        "model_name": (response_usage.get("model_name") or analysis_usage.get("model_name")),
        "model_provider": (response_usage.get("model_provider") or analysis_usage.get("model_provider")),
    }


def _build_graph(checkpointer: Any = None) -> Any:
    builder = StateGraph(DSALearnState)
    builder.add_node("detect_mode", _detect_mode_node)
    builder.add_node("analyze_turn", _analyze_turn_node)
    builder.add_node("learn_response", _learn_response_node)
    builder.add_node("reflection_response", _reflection_response_node)
    builder.add_edge(START, "detect_mode")
    builder.add_edge("detect_mode", "analyze_turn")
    builder.add_conditional_edges(
        "analyze_turn",
        _route_after_analysis,
        {
            "learn_response": "learn_response",
            "reflection_response": "reflection_response",
        },
    )
    builder.add_edge("learn_response", END)
    builder.add_edge("reflection_response", END)
    return builder.compile(checkpointer=checkpointer)


# Compiled without a checkpointer initially; replaced at startup via init_graph().
_DSA_LEARN_GRAPH = _build_graph()


def init_graph(checkpointer: Any) -> None:
    """Recompile the graph with a persistent checkpointer. Called once at startup."""
    global _DSA_LEARN_GRAPH
    _DSA_LEARN_GRAPH = _build_graph(checkpointer)


async def generate_dsa_learn_turn(
    *,
    topic: str,
    language: str = "english",
    problem_statement: str,
    prior_knowledge: str | None,
    history_excerpt: str | None,
    user_message: str,
    thread_id: str,
) -> tuple[str, dict[str, Any], list[dict[str, str]], LLMUsagePayload]:
    prompt_inputs = build_dsa_learn_prompt_inputs(
        topic=topic,
        language=language,
        problem_statement=problem_statement,
        prior_knowledge=prior_knowledge,
        history_excerpt=history_excerpt,
        last_user_message=user_message,
    )
    result = await _DSA_LEARN_GRAPH.ainvoke(prompt_inputs, config={"configurable": {"thread_id": thread_id}})
    assistant_message = str(result.get("assistant_message") or "").strip()
    if not assistant_message:
        raise ValueError("DSA learn agent did not return an assistant message")
    return (
        assistant_message,
        result.get("analysis") or {},
        result.get("weak_area_signals") or [],
        _build_usage_totals(result.get("analysis_usage"), result.get("response_usage")),
    )
