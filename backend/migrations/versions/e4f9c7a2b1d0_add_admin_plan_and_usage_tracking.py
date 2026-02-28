"""add admin, plan, and usage tracking

Revision ID: e4f9c7a2b1d0
Revises: b5f2e4d9a731
Create Date: 2026-02-28 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f9c7a2b1d0"
down_revision: Union[str, Sequence[str], None] = "b5f2e4d9a731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("plan_type", sa.String(length=20), nullable=False, server_default=sa.text("'free'")),
    )
    op.add_column("users", sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_users_plan_type",
        "users",
        "plan_type IN ('free', 'premium')",
    )

    op.add_column("lessons", sa.Column("content_generated_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_usage_events_id"), "llm_usage_events", ["id"], unique=False)
    op.create_index(op.f("ix_llm_usage_events_user_id"), "llm_usage_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_llm_usage_events_created_at"), "llm_usage_events", ["created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_llm_usage_events_created_at"), table_name="llm_usage_events")
    op.drop_index(op.f("ix_llm_usage_events_user_id"), table_name="llm_usage_events")
    op.drop_index(op.f("ix_llm_usage_events_id"), table_name="llm_usage_events")
    op.drop_table("llm_usage_events")

    op.drop_column("lessons", "content_generated_at")

    op.drop_constraint("ck_users_plan_type", "users", type_="check")
    op.drop_column("users", "trial_expires_at")
    op.drop_column("users", "plan_type")
    op.drop_column("users", "is_admin")
