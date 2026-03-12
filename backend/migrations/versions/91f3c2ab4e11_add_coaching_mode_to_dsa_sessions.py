"""add coaching mode to dsa sessions

Revision ID: 91f3c2ab4e11
Revises: 7c1e3f9a8d42
Create Date: 2026-03-13 00:20:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "91f3c2ab4e11"
down_revision: Union[str, Sequence[str], None] = "7c1e3f9a8d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "dsa_coach_sessions",
        sa.Column(
            "coaching_mode",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'solve_problem'"),
        ),
    )
    op.create_check_constraint(
        "ck_dsa_coach_sessions_coaching_mode",
        "dsa_coach_sessions",
        "coaching_mode IN ('learn_topic', 'solve_problem')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_dsa_coach_sessions_coaching_mode", "dsa_coach_sessions", type_="check")
    op.drop_column("dsa_coach_sessions", "coaching_mode")
