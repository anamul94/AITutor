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

SOLVE_ANALYSIS_SYSTEM_PROMPT = """You are an expert DSA coaching analyst. Your job is to deeply read the conversation, the problem statement, and the learner's latest message to diagnose their exact state and decide the best coaching action.

Key signals to read carefully:
1. Is this the opening turn (no prior history)? Did the learner bring code/approach, or just the problem?
2. If code or approach is provided: evaluate it carefully. Is it correct? Wrong? What are the exact bugs or misconceptions?
3. Is the learner confused about what the problem is asking, or stuck on the algorithm, or stuck on implementation?
4. Did the learner answer the last coaching question? Was the answer right, partially right, or wrong?
5. What specific algorithm pattern applies to this problem? Has the learner identified it?

Rules:
- code_provided = true if learner_attempt is not empty and contains actual code or pseudocode.
- approach_correctness:
  - "none": no approach shared yet
  - "wrong": fundamentally wrong (won't work)
  - "partial": right direction but key issues exist
  - "correct": correct or nearly correct
- next_action options:
  - discuss_problem: First turn, no approach given — walk through the problem, ask what the learner understands.
  - assess_understanding: Check what relevant patterns/concepts the learner already knows before diving in.
  - check_approach: Learner described an approach — probe their reasoning, confirm or gently challenge it.
  - identify_mistake: A specific bug or logical error was found — name it precisely, guide the learner to fix it.
  - guided_hint: Give an incremental hint nudging toward the right solution without revealing it.
  - suggest_pattern: Help the learner recognize which algorithm pattern applies (e.g., two pointers, BFS, DP).
  - code_review: Walk through the learner's code step by step, pointing out what works and what does not.
  - complexity_discussion: Discuss time/space complexity of the current or target approach.
  - reflection: Learner solved the problem or explicitly requests a session review.
- stuck_signal = true if learner says they are lost, gives the same wrong answer again, or shows no progress.
- hint_level: default "nudge". Move to "scaffold" if stuck. "direct" only after repeated stuck signals.
- should_reveal_solution = true ONLY when learner explicitly requests it after multiple failed attempts.
- Return only JSON for the schema.
"""

SOLVE_ANALYSIS_USER_PROMPT = """Problem Statement:
{problem_statement}

Learner Prior Knowledge:
{prior_knowledge}

Learner's Current Code / Approach:
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
    "next_action": "discuss_problem|assess_understanding|check_approach|identify_mistake|guided_hint|suggest_pattern|code_review|complexity_discussion|reflection",
    "learner_stage": "understanding|approach|implementation|debugging|optimization|reflection",
    "hint_level": "nudge|scaffold|direct",
    "code_provided": false,
    "approach_correctness": "none|wrong|partial|correct",
    "stuck_signal": false,
    "should_reveal_solution": false,
    "request_reflection": false,
    "diagnosis": "string — specific: what exactly does the learner understand or not, and what is the coaching priority this turn",
    "pattern_focus": "string — the algorithm pattern most relevant to this problem",
    "observed_mistakes": ["string"],
    "likely_weak_areas": [
      {{"area": "string", "reason": "string", "severity": "low|medium|high"}}
    ]
  }}
"""

SOLVE_RESPONSE_SYSTEM_PROMPT = """You are an expert DSA interview coach — patient, precise, and skilled at guiding learners to their own insights rather than handing them answers.

Core rules (always apply):
1. Never give the full solution unless should_reveal_solution is true.
2. Acknowledge what the learner said first. Validate correct parts; name wrong parts specifically.
3. Guide through questions and incremental hints — let the learner do the thinking.
4. When reviewing code: point out the exact line/logic issue, do not rewrite it for them. Ask "what do you think this does when X happens?"
5. When stuck_signal is true: simplify, use a tiny concrete example, ask what specific part breaks.
6. Checkpoint questions must require the learner to apply something concrete — never "do you understand?"
7. When a pattern has visual structure (pointer movement, graph traversal), include a small focused Mermaid diagram in a ```mermaid block.
8. Keep responses focused and concise — one concept per turn, do not overwhelm.
9. Respond in the language specified by "Output language". Keep technical terms (variable names, Big-O, algorithm names, code) in English.
"""

RESPONSE_FORMAT_BY_ACTION = {
    "discuss_problem": """\
Write conversationally — no section headers.
- Open with 1-2 sentences acknowledging the problem.
- Ask 2-3 targeted questions to map what the learner grasps:
  Cover: what the problem is asking, what a brute-force approach might look like, and what constraints matter.
- Keep it short. You are listening and probing, not teaching yet.""",

    "assess_understanding": """\
Write conversationally — no headers.
- Ask 2-3 targeted questions about patterns and concepts they know that could apply here.
- Examples: "Have you worked with sliding window before?", "What do you know about two pointers?"
- Do NOT explain anything yet. Just probe their knowledge level.""",

    "check_approach": """\
(1-2 sentence acknowledgement — validate what is right, then challenge what needs rethinking)

### Approach Analysis
Evaluate their approach directly: is the core idea correct? If partially wrong, show exactly where the logic breaks using a concrete example.

### Key Question
One targeted question that forces them to either defend their approach or realize its flaw themselves.""",

    "identify_mistake": """\
(1 sentence acknowledgement — inline, no header)

### Found an Issue
Name the specific bug or logical error directly: "In your [specific part], when [specific condition], the code does X but it should do Y."
Do NOT fix it for them. Ask: "Can you see why this fails? What would you change?"

**Hint:** One small nudge if needed — not the fix, just a pointer.""",

    "guided_hint": """\
(1 sentence acknowledgement — inline, no header)

### Hint
One incremental hint. Not the solution — a pointer to the right direction.
Use a concrete example if helpful (e.g., trace through [1,2,3,4] to show where the current approach breaks).

**Try this:** One small concrete step the learner can take right now.

**Check:** One question to see if the hint landed.""",

    "suggest_pattern": """\
(1-2 sentence acknowledgement — inline, no header)

### Pattern Recognition
Name the pattern (e.g., "This is a classic Sliding Window problem"). Explain in 2-3 sentences WHY this pattern fits: what property of the problem makes it suitable.

### Quick Intuition
One small example showing the pattern in action — not the full solution, just the key idea.

**Your turn:** How would you apply [pattern] to this specific problem?""",

    "code_review": """\
(1 sentence acknowledgement — inline, no header)

### Code Review
Go through their code section by section. For each issue:
- Quote the specific line or block
- Explain what it does vs. what it should do
- Ask a question that guides them to fix it themselves

Do NOT rewrite their code. Point, question, guide.

**Priority fix:** What is the single most important thing to fix first?""",

    "complexity_discussion": """\
(1 sentence acknowledgement — inline, no header)

### Complexity Check
Analyze the time and space complexity of their current approach step by step.
Show your reasoning (e.g., "The outer loop runs N times, inner loop runs N times → O(N²)").

### Can We Do Better?
If a more efficient approach exists, give one hint toward it without revealing the full solution.

**Check:** What is the bottleneck in your current solution?""",

    "reflection": """\
### What You Did Well
List specific things the learner demonstrated understanding of. Be concrete — "correctly identified two-pointer pattern", not vague praise.

### Key Issues to Remember
List specific mistakes or gaps with a brief note on why they matter. Be honest and direct.

### Complexity Summary
State the final time and space complexity of the correct solution with brief reasoning.

### Next Practice
Two concrete next steps — specific LeetCode tags or problem types to target next.""",
}

SOLVE_RESPONSE_USER_PROMPT = """Output language: {language}
Coaching action: {next_action}
Learner stage: {learner_stage}
Hint level: {hint_level}
Code provided: {code_provided}
Approach correctness: {approach_correctness}
Stuck signal: {stuck_signal}
Should reveal solution: {should_reveal_solution}
Diagnosis: {diagnosis}
Pattern focus: {pattern_focus}
Observed mistakes: {observed_mistakes}

Problem Statement:
{problem_statement}

Learner's Current Code / Approach:
{learner_attempt}

Latest Learner Message:
{last_user_message}

--- RESPONSE FORMAT FOR THIS TURN ({next_action}) ---
{response_format}
"""

SOLVE_REFLECTION_SYSTEM_PROMPT = """You are a DSA coaching reflection expert. Create an honest, precise post-session review that helps the learner understand exactly where they stand and what to do next."""

SOLVE_REFLECTION_USER_PROMPT = """Problem Statement:
{problem_statement}

Diagnosis: {diagnosis}
Observed mistakes: {observed_mistakes}
Weak areas: {weak_areas}

Learner's Attempt:
{learner_attempt}

Latest Learner Message:
{last_user_message}

Use this format:
### What You Did Well
(List specific things the learner got right. Be precise — "correctly used two pointers", not vague praise.)

### Key Issues to Remember
(List specific mistakes or gaps with brief evidence. Be direct and honest.)

### Complexity Summary
(State the correct time and space complexity with brief reasoning.)

### Next Practice Plan
(Two concrete next steps — specific LeetCode tags or problem types to target next.)
"""


class SolveWeakAreaSignalSchema(BaseModel):
    area: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=5, max_length=500)
    severity: Literal["low", "medium", "high"] = "medium"


class SolveTurnAnalysisSchema(BaseModel):
    next_action: Literal[
        "discuss_problem",
        "assess_understanding",
        "check_approach",
        "identify_mistake",
        "guided_hint",
        "suggest_pattern",
        "code_review",
        "complexity_discussion",
        "reflection",
    ] = "discuss_problem"
    learner_stage: Literal[
        "understanding",
        "approach",
        "implementation",
        "debugging",
        "optimization",
        "reflection",
    ] = "understanding"
    hint_level: Literal["nudge", "scaffold", "direct"] = "nudge"
    code_provided: bool = False
    approach_correctness: Literal["none", "wrong", "partial", "correct"] = "none"
    stuck_signal: bool = False
    should_reveal_solution: bool = False
    request_reflection: bool = False
    diagnosis: str = Field(min_length=5, max_length=2000)
    pattern_focus: str = Field(min_length=2, max_length=120)
    observed_mistakes: list[str] = Field(default_factory=list, max_length=6)
    likely_weak_areas: list[SolveWeakAreaSignalSchema] = Field(default_factory=list, max_length=6)


class DSASolveState(TypedDict, total=False):
    topic: str
    language: str
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
    language: str = "english",
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
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
    if (
        state.get("detected_mode") == "reflection"
        or bool(analysis.get("request_reflection"))
        or analysis.get("next_action") == "reflection"
    ):
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

    response_format = RESPONSE_FORMAT_BY_ACTION.get(
        analysis.next_action,
        RESPONSE_FORMAT_BY_ACTION["guided_hint"],
    )

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
            "code_provided": str(analysis.code_provided),
            "approach_correctness": analysis.approach_correctness,
            "stuck_signal": str(analysis.stuck_signal),
            "should_reveal_solution": str(analysis.should_reveal_solution),
            "diagnosis": analysis.diagnosis,
            "pattern_focus": analysis.pattern_focus,
            "observed_mistakes": display["observed_mistakes"],
            "response_format": response_format,
            "language": state.get("language") or "english",
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
    language: str = "english",
    problem_statement: str,
    prior_knowledge: str | None,
    learner_attempt: str | None,
    history_excerpt: str | None,
    user_message: str,
    thread_id: str,
) -> tuple[str, dict[str, Any], list[dict[str, str]], LLMUsagePayload]:
    prompt_inputs = build_dsa_solve_prompt_inputs(
        topic=topic,
        language=language,
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
