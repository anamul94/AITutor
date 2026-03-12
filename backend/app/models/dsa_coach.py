from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.user import Base


class DSACoachSession(Base):
    __tablename__ = "dsa_coach_sessions"
    __table_args__ = (
        CheckConstraint(
            "topic IN ('arrays', 'sliding_window', 'binary_search', 'graphs', "
            "'recursion', 'dynamic_programming', 'general_problem_solving')",
            name="ck_dsa_coach_sessions_topic",
        ),
        CheckConstraint(
            "coaching_mode IN ('learn_topic', 'solve_problem')",
            name="ck_dsa_coach_sessions_coaching_mode",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_dsa_coach_sessions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(50), nullable=False)
    coaching_mode = Column(
        String(20),
        nullable=False,
        default="solve_problem",
        server_default=text("'solve_problem'"),
    )
    prior_knowledge = Column(Text, nullable=True)
    problem_statement = Column(Text, nullable=False)
    learner_attempt = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", backref="dsa_coach_sessions")
    turns = relationship(
        "DSACoachTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DSACoachTurn.created_at",
    )


class DSACoachTurn(Base):
    __tablename__ = "dsa_coach_turns"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_dsa_coach_turns_role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("dsa_coach_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    turn_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    session = relationship("DSACoachSession", back_populates="turns")


class DSAWeakArea(Base):
    __tablename__ = "dsa_weak_areas"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", "area", name="uq_dsa_weak_areas_user_topic_area"),
        CheckConstraint("severity_score BETWEEN 1 AND 3", name="ck_dsa_weak_areas_severity_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(50), nullable=False)
    area = Column(String(120), nullable=False)
    evidence = Column(Text, nullable=True)
    severity_score = Column(Integer, nullable=False, default=1, server_default=text("1"))
    occurrence_count = Column(Integer, nullable=False, default=1, server_default=text("1"))
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    owner = relationship("User", backref="dsa_weak_areas")
