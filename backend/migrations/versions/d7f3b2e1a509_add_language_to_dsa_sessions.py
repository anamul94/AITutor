"""add language column to dsa_coach_sessions

Revision ID: d7f3b2e1a509
Revises: c4e8a1f2d093
Create Date: 2026-03-13 00:00:05.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d7f3b2e1a509"
down_revision: Union[str, Sequence[str], None] = "c4e8a1f2d093"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dsa_coach_sessions",
        sa.Column(
            "language",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'english'"),
        ),
    )
    op.create_check_constraint(
        "ck_dsa_coach_sessions_language",
        "dsa_coach_sessions",
        "language IN ('english', 'bengali', 'hindi')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_dsa_coach_sessions_language", "dsa_coach_sessions", type_="check")
    op.drop_column("dsa_coach_sessions", "language")
