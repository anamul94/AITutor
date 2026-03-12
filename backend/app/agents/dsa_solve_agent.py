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

SOLVE_ANALYSIS_SYSTEM_PROMPT = """You are a DSA problem-solving coach for interview prep.

Mission:
- Help learner solve the given problem through reasoning, not answer dumping.

Rules:
1. First identify the learner's current stage and likely pattern.
2. If learner has not shared initial thought, ask for it first.
3. If learner says they do not understand problem, rephrase clearly with a tiny example.
4. Keep hints incremental and avoid full solution unless explicitly requested or learner is stuck repeatedly.
5. Return only JSON for the schema.
"""

SOLVE_ANALYSIS_USER_PROMPT = """Mode: solve_problem
Topic: {topic}
Problem Statement:
{problem_statement}

Learner Prior Knowledge:
{prior_knowledge}

Learner Attempt:
{learner_attempt}

Recent Conversation:
{history_excerpt}

Latest Learner Message:
{last_user_message}
"""

SOLVE_ANALYSIS_OPENAI_JSON_RULES = """
Output format requirements:
- Return ONLY valid JSON.
- Do NOT use markdown code fences.
- Do NOT add any text before or after the JSON.
- JSON shape:
  {{
    "next_action": "ask_initial_thought|concept_clarification|pattern_selection|guided_hint|reflection",
    "learner_stage": "understanding|decomposition|approach|implementation|debugging|complexity|reflection",
    "hint_level": "nudge|scaffold|direct",
    "should_offer_solution": false,
    "request_reflection": false,
    "diagnosis": "string",
    "pattern_focus": "string",
    "observed_mistakes": ["string"],
    "likely_weak_areas": [
      {{"area": "string", "reason": "string", "severity": "low|medium|high"}}
    ]
  }}
"""

SOLVE_RESPONSE_SYSTEM_PROMPT = """You are a patient DSA interview coach.

Strict behavior:
1. Prioritize pattern recognition and decomposition.
2. Do not provide full final code unless should_offer_solution is true.
3. Ask one strong checkpoint question each turn.
4. Include one concrete next action the learner can do immediately.
5. Keep tone direct and concise.
6. If learner is confused, simplify with tiny example then return to the original problem.
7. Mention complexity reasoning whenever relevant.
8. Avoid generic advice; response must be specific to current problem details.
"""

SOLVE_RESPONSE_USER_PROMPT = """Topic: {topic}
Next action: {next_action}
Learner stage: {learner_stage}
Hint level: {hint_level}
Should offer solution: {should_offer_solution}
Diagnosis: {diagnosis}
Pattern focus: {pattern_focus}
Observed mistakes: {observed_mistakes}

Problem Statement:
{problem_statement}

Learner Attempt:
{learner_attempt}

Latest Learner Message:
{last_user_message}

Respond in this format:
### Next Step
### Pattern Lens
### Hint
### Checkpoint Question
"""

SOLVE_REFLECTION_SYSTEM_PROMPT = """You are a DSA post-problem reflection coach.

Write brief reflection with:
1. What learner did well.
2. Biggest mistakes.
3. Complexity check.
4. One focused next practice.
"""

SOLVE_REFLECTION_USER_PROMPT = """Topic: {topic}
Diagnosis: {diagnosis}
Observed mistakes: {observed_mistakes}
Weak areas: {weak_areas}
Problem Statement:
{problem_statement}
Learner Attempt:
{learner_attempt}
Latest Learner Message:
{last_user_message}

Use this format:
### What Went Well
### Mistakes To Fix
### Complexity Check
### Next Practice
"""


class SolveWeakAreaSignalSchema(BaseModel):
    area: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=5, max_length=500)
    severity: Literal["low", "medium", "high"] = "medium"


class SolveTurnAnalysisSchema(BaseModel):
    next_action: Literal[
        "ask_initial_thought",
        "concept_clarification",
        "pattern_selection",
        "guided_hint",
        "reflection",
    ] = "guided_hint"
    learner_stage: Literal[
        "understanding",
        "decomposition",
        "approach",
        "implementation",
        "debugging",
        "complexity",
        "reflection",
    ] = "understanding"
    hint_level: Literal["nudge", "scaffold", "direct"] = "nudge"
    should_offer_solution: bool = False
    request_reflection: bool = False
    diagnosis: str = Field(min_length=5, max_length=2000)
    pattern_focus: str = Field(min_length=2, max_length=120)
    observed_mistakes: list[str] = Field(default_factory=list, max_length=6)
    likely_weak_areas: list[SolveWeakAreaSignalSchema] = Field(default_factory=list, max_length=6)


class DSASolveState(TypedDict, total=False):
    topic: str
    problem_statement: str
    prior_knowledge: str
    learner_attempt: str
    history_excerpt: str
    last_user_message: str
    detected_mode: str
    analysis: dict[str, Any]
    assistant_message: str
    weak_area_signals: list[dict[str, str]]
    analysis_usage: LLMUsagePayload
    response_usage: LLMUsagePayload


def build_dsa_solve_prompt_inputs(
    *,
    topic: str,
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
    history_excerpt: str | None,
    last_user_message: str,
) -> dict[str, str]:
    return {
        "topic": topic.strip().lower(),
        "problem_statement": problem_statement.strip(),
        "prior_knowledge": (prior_knowledge or "").strip() or "Not provided",
        "learner_attempt": (learner_attempt or "").strip() or "Not provided",
        "history_excerpt": ((history_excerpt or "").strip() or "No prior turns yet.")[-8000:],
        "last_user_message": last_user_message.strip(),
    }


def _detect_mode_node(state: DSASolveState) -> dict[str, str]:
    message = (state.get("last_user_message") or "").lower()
    reflection_markers = ("i solved", "done", "review my mistakes", "postmortem", "reflect")
    detected_mode = "reflection" if any(marker in message for marker in reflection_markers) else "coach"
    return {"detected_mode": detected_mode}


async def _analyze_turn_node(state: DSASolveState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    is_openai_compatible = llm_context.get("provider") == "openai-compatible"

    usage_callback = UsageMetadataCallbackHandler()
    if is_openai_compatible:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SOLVE_ANALYSIS_SYSTEM_PROMPT),
            ("user", f"{SOLVE_ANALYSIS_USER_PROMPT}\n\n{SOLVE_ANALYSIS_OPENAI_JSON_RULES}"),
        ])
        chain = prompt | llm
        raw_result = await chain.ainvoke(state, config={"callbacks": [usage_callback]})
        analysis = parse_pydantic_from_response(raw_result, SolveTurnAnalysisSchema)
        raw_for_usage = raw_result
    else:
        structured_llm = llm.with_structured_output(SolveTurnAnalysisSchema, include_raw=True)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SOLVE_ANALYSIS_SYSTEM_PROMPT),
            ("user", SOLVE_ANALYSIS_USER_PROMPT),
        ])
        chain = prompt | structured_llm
        result = await chain.ainvoke(state, config={"callbacks": [usage_callback]})
        analysis = result.get("parsed")
        raw_for_usage = result.get("raw")
        if analysis is None:
            parsing_error = result.get("parsing_error")
            logger.warning(
                "Bedrock structured output failed to parse solve analysis (error=%s). Falling back to JSON parse.",
                parsing_error,
            )
            analysis = parse_pydantic_from_response(raw_for_usage, SolveTurnAnalysisSchema)

    usage = build_usage_payload(
        callback_usage_metadata=usage_callback.usage_metadata,
        raw_message=raw_for_usage,
        fallback_provider=llm_context.get("provider"),
        fallback_model=llm_context.get("configured_model"),
    )
    return {"analysis": analysis.model_dump(), "analysis_usage": usage}


def _route_after_analysis(state: DSASolveState) -> str:
    analysis = state.get("analysis") or {}
    if state.get("detected_mode") == "reflection" or bool(analysis.get("request_reflection")):
        return "reflection_response"
    return "solve_response"


def _analysis_to_strings(analysis: SolveTurnAnalysisSchema) -> dict[str, str]:
    mistakes = analysis.observed_mistakes or ["None explicitly identified yet."]
    weak_areas = [f"{item.area} ({item.severity})" for item in analysis.likely_weak_areas]
    return {
        "observed_mistakes": "; ".join(mistakes),
        "weak_areas": "; ".join(weak_areas) if weak_areas else "No clear weak area signal yet.",
    }


async def _solve_response_node(state: DSASolveState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    analysis = SolveTurnAnalysisSchema.model_validate(state.get("analysis") or {})
    display = _analysis_to_strings(analysis)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SOLVE_RESPONSE_SYSTEM_PROMPT),
        ("user", SOLVE_RESPONSE_USER_PROMPT),
    ])
    chain = prompt | llm
    usage_callback = UsageMetadataCallbackHandler()
    raw_result = await chain.ainvoke(
        {
            **state,
            "next_action": analysis.next_action,
            "learner_stage": analysis.learner_stage,
            "hint_level": analysis.hint_level,
            "should_offer_solution": str(analysis.should_offer_solution),
            "diagnosis": analysis.diagnosis,
            "pattern_focus": analysis.pattern_focus,
            "observed_mistakes": display["observed_mistakes"],
        },
        config={"callbacks": [usage_callback]},
    )
    assistant_message = response_content_to_text(getattr(raw_result, "content", raw_result)).strip()
    if not assistant_message:
        raise ValueError("Failed to generate DSA solve response")

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


async def _reflection_response_node(state: DSASolveState) -> dict[str, Any]:
    llm, llm_context = get_llm_client()
    analysis = SolveTurnAnalysisSchema.model_validate(state.get("analysis") or {})
    display = _analysis_to_strings(analysis)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SOLVE_REFLECTION_SYSTEM_PROMPT),
        ("user", SOLVE_REFLECTION_USER_PROMPT),
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
        raise ValueError("Failed to generate DSA solve reflection response")

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
    builder = StateGraph(DSASolveState)
    builder.add_node("detect_mode", _detect_mode_node)
    builder.add_node("analyze_turn", _analyze_turn_node)
    builder.add_node("solve_response", _solve_response_node)
    builder.add_node("reflection_response", _reflection_response_node)
    builder.add_edge(START, "detect_mode")
    builder.add_edge("detect_mode", "analyze_turn")
    builder.add_conditional_edges(
        "analyze_turn",
        _route_after_analysis,
        {
            "solve_response": "solve_response",
            "reflection_response": "reflection_response",
        },
    )
    builder.add_edge("solve_response", END)
    builder.add_edge("reflection_response", END)
    return builder.compile(checkpointer=checkpointer)


# Compiled without a checkpointer initially; replaced at startup via init_graph().
_DSA_SOLVE_GRAPH = _build_graph()


def init_graph(checkpointer: Any) -> None:
    """Recompile the graph with a persistent checkpointer. Called once at startup."""
    global _DSA_SOLVE_GRAPH
    _DSA_SOLVE_GRAPH = _build_graph(checkpointer)


async def generate_dsa_solve_turn(
    *,
    topic: str,
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
    history_excerpt: str | None,
    user_message: str,
    thread_id: str,
) -> tuple[str, dict[str, Any], list[dict[str, str]], LLMUsagePayload]:
    prompt_inputs = build_dsa_solve_prompt_inputs(
        topic=topic,
        problem_statement=problem_statement,
        prior_knowledge=prior_knowledge,
        learner_attempt=learner_attempt,
        history_excerpt=history_excerpt,
        last_user_message=user_message,
    )
    result = await _DSA_SOLVE_GRAPH.ainvoke(prompt_inputs, config={"configurable": {"thread_id": thread_id}})
    assistant_message = str(result.get("assistant_message") or "").strip()
    if not assistant_message:
        raise ValueError("DSA solve agent did not return an assistant message")
    return (
        assistant_message,
        result.get("analysis") or {},
        result.get("weak_area_signals") or [],
        _build_usage_totals(result.get("analysis_usage"), result.get("response_usage")),
    )
