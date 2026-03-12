from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.agents import generate_dsa_coaching_turn
from app.api.deps import get_current_user, get_db
from app.models.course import LLMUsageEvent
from app.models.dsa_coach import DSACoachSession, DSACoachTurn, DSAWeakArea
from app.models.user import User
from app.schemas.dsa_coach import (
    DSACoachingMode,
    DSACoachMessageRequest,
    DSACoachSessionCreateRequest,
    DSACoachSessionResponse,
    DSACoachSessionSummaryResponse,
    DSACoachTurnResultResponse,
    DSAWeakAreaResponse,
)

router = APIRouter()

DEFAULT_COACHING_OPENING = (
    "Please coach me through this problem step by step. "
    "Ask questions and avoid revealing the full solution too early."
)
DEFAULT_LEARN_TOPIC_OPENING = (
    "Teach me this topic from fundamentals, check prerequisite knowledge, "
    "then give me a practice problem and guide me step by step."
)
TOPIC_MODE_PROBLEM_TEMPLATE = (
    "Topic-first coaching mode for '{topic}'. Explain core ideas, check prerequisites, "
    "and transition to guided problem solving."
)
INITIAL_THOUGHT_PROMPT = (
    "Before I give hints, what is your initial thought about solving this problem?\n"
    "If you are stuck, say: 'I don't understand the problem yet' and I will break it down first."
)

SEVERITY_TO_SCORE = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _log_llm_usage(
    db: AsyncSession,
    user_id: int,
    operation: str,
    usage: dict[str, object] | None,
) -> None:
    usage = usage or {}
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens))
    model_name = usage.get("model_name")
    model_provider = usage.get("model_provider")
    db.add(
        LLMUsageEvent(
            user_id=user_id,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_name=str(model_name) if model_name else None,
            model_provider=str(model_provider) if model_provider else None,
        )
    )


def _build_history_excerpt(turns: list[DSACoachTurn], max_turns: int = 8) -> str:
    if not turns:
        return "No prior turns yet."

    recent_turns = turns[-max_turns:]
    lines: list[str] = []
    for turn in recent_turns:
        speaker = "Learner"
        if turn.role == "assistant":
            speaker = "Coach"
        elif turn.role == "system":
            speaker = "System"
        lines.append(f"{speaker}: {(turn.content or '').strip()}")
    joined = "\n".join(lines).strip()
    return joined[-8000:] if joined else "No prior turns yet."


def _serialize_turn(turn: DSACoachTurn) -> dict[str, Any]:
    return {
        "id": turn.id,
        "role": turn.role,
        "content": turn.content,
        "created_at": turn.created_at,
    }


def _serialize_session(session: DSACoachSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "topic": session.topic,
        "coaching_mode": session.coaching_mode,
        "problem_statement": session.problem_statement,
        "prior_knowledge": session.prior_knowledge,
        "learner_attempt": session.learner_attempt,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "turns": [_serialize_turn(turn) for turn in session.turns],
    }


def _serialize_weak_area(area: DSAWeakArea) -> dict[str, Any]:
    return {
        "id": area.id,
        "topic": area.topic,
        "area": area.area,
        "evidence": area.evidence,
        "severity_score": area.severity_score,
        "occurrence_count": area.occurrence_count,
        "first_seen_at": area.first_seen_at,
        "last_seen_at": area.last_seen_at,
    }


async def _get_session_or_404(
    db: AsyncSession,
    *,
    session_id: int,
    user_id: int,
    with_turns: bool = False,
) -> DSACoachSession:
    query = select(DSACoachSession).where(
        DSACoachSession.id == session_id,
        DSACoachSession.user_id == user_id,
    )
    if with_turns:
        query = query.options(selectinload(DSACoachSession.turns))
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="DSA coaching session not found")
    return session


async def _upsert_weak_areas(
    db: AsyncSession,
    *,
    user_id: int,
    topic: str,
    signals: list[dict[str, str]],
) -> list[DSAWeakArea]:
    if not signals:
        return []

    deduped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        area = str(signal.get("area") or "").strip()
        reason = str(signal.get("reason") or "").strip()
        severity_label = str(signal.get("severity") or "medium").lower()
        severity_score = SEVERITY_TO_SCORE.get(severity_label, 2)
        if not area:
            continue
        key = area.lower()
        existing = deduped.get(key)
        if not existing:
            deduped[key] = {
                "area": area[:120],
                "reason": reason[:2000] if reason else None,
                "severity_score": severity_score,
            }
            continue
        existing["severity_score"] = max(existing["severity_score"], severity_score)
        if reason:
            existing["reason"] = reason[:2000]

    updates: list[DSAWeakArea] = []
    now = datetime.now(timezone.utc)
    for signal in deduped.values():
        area_result = await db.execute(
            select(DSAWeakArea).where(
                DSAWeakArea.user_id == user_id,
                DSAWeakArea.topic == topic,
                DSAWeakArea.area == signal["area"],
            )
        )
        weak_area = area_result.scalar_one_or_none()
        if weak_area:
            weak_area.occurrence_count = int(weak_area.occurrence_count or 0) + 1
            weak_area.severity_score = max(int(weak_area.severity_score or 1), signal["severity_score"])
            if signal.get("reason"):
                weak_area.evidence = signal["reason"]
            weak_area.last_seen_at = now
        else:
            weak_area = DSAWeakArea(
                user_id=user_id,
                topic=topic,
                area=signal["area"],
                evidence=signal.get("reason"),
                severity_score=signal["severity_score"],
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(weak_area)
        updates.append(weak_area)

    await db.flush()
    return updates


@router.post("/sessions", response_model=DSACoachSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_dsa_coaching_session(
    request: DSACoachSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    opening_message = request.message or DEFAULT_COACHING_OPENING
    if request.coaching_mode == "learn_topic":
        opening_message = request.message or DEFAULT_LEARN_TOPIC_OPENING

    effective_problem_statement = request.problem_statement
    if request.coaching_mode == "learn_topic":
        effective_problem_statement = TOPIC_MODE_PROBLEM_TEMPLATE.format(
            topic=request.topic.replace("_", " ")
        )

    effective_learner_attempt = request.learner_attempt if request.coaching_mode == "solve_problem" else None

    session = DSACoachSession(
        user_id=current_user.id,
        topic=request.topic,
        coaching_mode=request.coaching_mode,
        problem_statement=effective_problem_statement or "",
        prior_knowledge=request.prior_knowledge,
        learner_attempt=effective_learner_attempt,
        status="active",
    )
    db.add(session)
    await db.flush()

    db.add(
        DSACoachTurn(
            session_id=session.id,
            role="user",
            content=opening_message,
        )
    )
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    if request.coaching_mode == "solve_problem" and request.message is None:
        assistant_turn = DSACoachTurn(
            session_id=session.id,
            role="assistant",
            content=INITIAL_THOUGHT_PROMPT,
            turn_metadata={
                "analysis": {
                    "next_action": "ask_initial_thought",
                    "learner_stage": "understanding",
                    "hint_level": "nudge",
                }
            },
        )
        db.add(assistant_turn)
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        final_session = await _get_session_or_404(
            db,
            session_id=session.id,
            user_id=current_user.id,
            with_turns=True,
        )
        return _serialize_session(final_session)

    session_with_turns = await _get_session_or_404(
        db,
        session_id=session.id,
        user_id=current_user.id,
        with_turns=True,
    )
    history_excerpt = _build_history_excerpt(session_with_turns.turns)

    try:
        assistant_message, analysis, weak_area_signals, usage = await generate_dsa_coaching_turn(
            coaching_mode=session_with_turns.coaching_mode,
            topic=session_with_turns.topic,
            problem_statement=session_with_turns.problem_statement,
            prior_knowledge=session_with_turns.prior_knowledge,
            learner_attempt=session_with_turns.learner_attempt,
            history_excerpt=history_excerpt,
            user_message=opening_message,
            thread_id=f"dsa-session-{session_with_turns.id}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DSA coaching generation failed: {exc}") from exc

    assistant_turn = DSACoachTurn(
        session_id=session_with_turns.id,
        role="assistant",
        content=assistant_message,
        turn_metadata={"analysis": analysis},
    )
    db.add(assistant_turn)
    session_with_turns.updated_at = datetime.now(timezone.utc)
    await _upsert_weak_areas(
        db,
        user_id=current_user.id,
        topic=session_with_turns.topic,
        signals=weak_area_signals,
    )
    _log_llm_usage(db, current_user.id, "dsa_coaching_turn", usage)
    await db.commit()

    final_session = await _get_session_or_404(
        db,
        session_id=session_with_turns.id,
        user_id=current_user.id,
        with_turns=True,
    )
    return _serialize_session(final_session)


@router.get("/sessions", response_model=list[DSACoachSessionSummaryResponse])
async def list_dsa_coaching_sessions(
    coaching_mode: DSACoachingMode | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(DSACoachSession)
        .options(selectinload(DSACoachSession.turns))
        .where(DSACoachSession.user_id == current_user.id)
    )
    if coaching_mode:
        query = query.where(DSACoachSession.coaching_mode == coaching_mode)

    result = await db.execute(
        query.order_by(desc(DSACoachSession.updated_at), desc(DSACoachSession.id)).limit(100)
    )
    sessions = result.scalars().all()

    summaries: list[dict[str, Any]] = []
    for session in sessions:
        latest_assistant_preview = None
        for turn in reversed(session.turns):
            if turn.role == "assistant":
                latest_assistant_preview = (turn.content or "").strip()
                if len(latest_assistant_preview) > 140:
                    latest_assistant_preview = f"{latest_assistant_preview[:137]}..."
                break
        latest_concept_focus = None
        for turn in reversed(session.turns):
            if turn.role == "assistant" and isinstance(turn.turn_metadata, dict):
                analysis = turn.turn_metadata.get("analysis", {})
                if isinstance(analysis, dict):
                    latest_concept_focus = analysis.get("concept_focus") or None
                break

        summaries.append(
            {
                "id": session.id,
                "topic": session.topic,
                "coaching_mode": session.coaching_mode,
                "status": session.status,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "turns_count": len(session.turns),
                "latest_assistant_preview": latest_assistant_preview,
                "concept_focus": latest_concept_focus,
            }
        )
    return summaries


@router.get("/sessions/{session_id}", response_model=DSACoachSessionResponse)
async def get_dsa_coaching_session(
    session_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_session_or_404(
        db,
        session_id=session_id,
        user_id=current_user.id,
        with_turns=True,
    )
    return _serialize_session(session)


@router.post("/sessions/{session_id}/messages", response_model=DSACoachTurnResultResponse)
async def send_dsa_coaching_message(
    request: DSACoachMessageRequest,
    session_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_session_or_404(
        db,
        session_id=session_id,
        user_id=current_user.id,
        with_turns=False,
    )

    if session.coaching_mode == "solve_problem" and request.learner_attempt is not None:
        session.learner_attempt = request.learner_attempt

    user_turn = DSACoachTurn(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_turn)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    session_with_turns = await _get_session_or_404(
        db,
        session_id=session.id,
        user_id=current_user.id,
        with_turns=True,
    )
    history_excerpt = _build_history_excerpt(session_with_turns.turns)

    try:
        assistant_message, analysis, weak_area_signals, usage = await generate_dsa_coaching_turn(
            coaching_mode=session_with_turns.coaching_mode,
            topic=session_with_turns.topic,
            problem_statement=session_with_turns.problem_statement,
            prior_knowledge=session_with_turns.prior_knowledge,
            learner_attempt=session_with_turns.learner_attempt,
            history_excerpt=history_excerpt,
            user_message=request.message,
            thread_id=f"dsa-session-{session_with_turns.id}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DSA coaching generation failed: {exc}") from exc

    assistant_turn = DSACoachTurn(
        session_id=session_with_turns.id,
        role="assistant",
        content=assistant_message,
        turn_metadata={"analysis": analysis},
    )
    db.add(assistant_turn)
    session_with_turns.updated_at = datetime.now(timezone.utc)

    weak_area_updates = await _upsert_weak_areas(
        db,
        user_id=current_user.id,
        topic=session_with_turns.topic,
        signals=weak_area_signals,
    )
    _log_llm_usage(db, current_user.id, "dsa_coaching_turn", usage)
    await db.commit()

    analysis_stage = analysis.get("learner_stage") if isinstance(analysis, dict) else None
    hint_level = analysis.get("hint_level") if isinstance(analysis, dict) else None
    concept_focus = analysis.get("concept_focus") if isinstance(analysis, dict) else None
    next_action = analysis.get("next_action") if isinstance(analysis, dict) else None
    return {
        "session_id": session_with_turns.id,
        "assistant_turn": _serialize_turn(assistant_turn),
        "coaching_stage": analysis_stage,
        "hint_level": hint_level,
        "concept_focus": concept_focus,
        "next_action": next_action,
        "weak_area_updates": [_serialize_weak_area(area) for area in weak_area_updates],
    }


@router.get("/weak-areas", response_model=list[DSAWeakAreaResponse])
async def list_dsa_weak_areas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DSAWeakArea)
        .where(DSAWeakArea.user_id == current_user.id)
        .order_by(
            desc(DSAWeakArea.occurrence_count),
            desc(DSAWeakArea.severity_score),
            desc(DSAWeakArea.last_seen_at),
        )
        .limit(100)
    )
    weak_areas = result.scalars().all()
    return [_serialize_weak_area(area) for area in weak_areas]
