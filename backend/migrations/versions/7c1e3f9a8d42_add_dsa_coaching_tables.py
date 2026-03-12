"""add dsa coaching tables

Revision ID: 7c1e3f9a8d42
Revises: 3a21d2fd8f91
Create Date: 2026-03-13 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1e3f9a8d42"
down_revision: Union[str, Sequence[str], None] = "3a21d2fd8f91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dsa_coach_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=50), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("learner_attempt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "topic IN ('arrays', 'sliding_window', 'binary_search', 'graphs', 'recursion', "
            "'dynamic_programming', 'general_problem_solving')",
            name="ck_dsa_coach_sessions_topic",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_dsa_coach_sessions_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dsa_coach_sessions_id"), "dsa_coach_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_dsa_coach_sessions_user_id"), "dsa_coach_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_dsa_coach_sessions_updated_at"), "dsa_coach_sessions", ["updated_at"], unique=False)

    op.create_table(
        "dsa_coach_turns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_dsa_coach_turns_role"),
        sa.ForeignKeyConstraint(["session_id"], ["dsa_coach_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dsa_coach_turns_id"), "dsa_coach_turns", ["id"], unique=False)
    op.create_index(op.f("ix_dsa_coach_turns_session_id"), "dsa_coach_turns", ["session_id"], unique=False)
    op.create_index(op.f("ix_dsa_coach_turns_created_at"), "dsa_coach_turns", ["created_at"], unique=False)

    op.create_table(
        "dsa_weak_areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=50), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("severity_score", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("severity_score BETWEEN 1 AND 3", name="ck_dsa_weak_areas_severity_score"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic", "area", name="uq_dsa_weak_areas_user_topic_area"),
    )
    op.create_index(op.f("ix_dsa_weak_areas_id"), "dsa_weak_areas", ["id"], unique=False)
    op.create_index(op.f("ix_dsa_weak_areas_user_id"), "dsa_weak_areas", ["user_id"], unique=False)
    op.create_index(op.f("ix_dsa_weak_areas_last_seen_at"), "dsa_weak_areas", ["last_seen_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_dsa_weak_areas_last_seen_at"), table_name="dsa_weak_areas")
    op.drop_index(op.f("ix_dsa_weak_areas_user_id"), table_name="dsa_weak_areas")
    op.drop_index(op.f("ix_dsa_weak_areas_id"), table_name="dsa_weak_areas")
    op.drop_table("dsa_weak_areas")

    op.drop_index(op.f("ix_dsa_coach_turns_created_at"), table_name="dsa_coach_turns")
    op.drop_index(op.f("ix_dsa_coach_turns_session_id"), table_name="dsa_coach_turns")
    op.drop_index(op.f("ix_dsa_coach_turns_id"), table_name="dsa_coach_turns")
    op.drop_table("dsa_coach_turns")

    op.drop_index(op.f("ix_dsa_coach_sessions_updated_at"), table_name="dsa_coach_sessions")
    op.drop_index(op.f("ix_dsa_coach_sessions_user_id"), table_name="dsa_coach_sessions")
    op.drop_index(op.f("ix_dsa_coach_sessions_id"), table_name="dsa_coach_sessions")
    op.drop_table("dsa_coach_sessions")
