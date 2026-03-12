from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

DSATopic = Literal[
    "arrays",
    "linked_lists",
    "stacks_and_queues",
    "sliding_window",
    "two_pointers",
    "binary_search",
    "sorting",
    "hashing",
    "trees",
    "binary_search_tree",
    "heaps",
    "graphs",
    "recursion",
    "backtracking",
    "dynamic_programming",
    "greedy",
    "tries",
    "bit_manipulation",
    "string_manipulation",
    "intervals",
    "matrix",
    "general_problem_solving",
]
DSATurnRole = Literal["user", "assistant", "system"]
DSACoachingMode = Literal["learn_topic", "solve_problem"]


class DSACoachSessionCreateRequest(BaseModel):
    topic: DSATopic
    coaching_mode: DSACoachingMode = "solve_problem"
    problem_statement: Optional[str] = Field(default=None, min_length=20, max_length=12000)
    prior_knowledge: Optional[str] = Field(default=None, max_length=2000)
    learner_attempt: Optional[str] = Field(default=None, max_length=12000)
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("problem_statement", mode="before")
    @classmethod
    def normalize_problem_statement(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("learner_attempt", mode="before")
    @classmethod
    def normalize_learner_attempt(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("prior_knowledge", mode="before")
    @classmethod
    def normalize_prior_knowledge(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("problem_statement")
    @classmethod
    def enforce_problem_statement_for_solve_mode(cls, value: Optional[str], info):
        mode = info.data.get("coaching_mode", "solve_problem")
        if mode == "solve_problem" and not value:
            raise ValueError("problem_statement is required for solve_problem mode")
        return value


class DSACoachMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    learner_attempt: Optional[str] = Field(default=None, max_length=12000)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("learner_attempt", mode="before")
    @classmethod
    def normalize_learner_attempt(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class DSACoachTurnResponse(BaseModel):
    id: int
    role: DSATurnRole
    content: str
    created_at: datetime


class DSACoachSessionSummaryResponse(BaseModel):
    id: int
    topic: DSATopic
    coaching_mode: DSACoachingMode
    status: str
    created_at: datetime
    updated_at: datetime
    turns_count: int
    latest_assistant_preview: Optional[str] = None
    concept_focus: Optional[str] = None


class DSACoachSessionResponse(BaseModel):
    id: int
    topic: DSATopic
    coaching_mode: DSACoachingMode
    problem_statement: str
    prior_knowledge: Optional[str] = None
    learner_attempt: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    turns: List[DSACoachTurnResponse] = Field(default_factory=list)


class DSAWeakAreaResponse(BaseModel):
    id: int
    topic: DSATopic
    area: str
    evidence: Optional[str] = None
    severity_score: int
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class DSACoachTurnResultResponse(BaseModel):
    session_id: int
    assistant_turn: DSACoachTurnResponse
    coaching_stage: Optional[str] = None
    hint_level: Optional[str] = None
    concept_focus: Optional[str] = None
    next_action: Optional[str] = None
    weak_area_updates: List[DSAWeakAreaResponse] = Field(default_factory=list)
