"""add learning goal and preferred level to courses

Revision ID: 8f3a3e1325f4
Revises: c16a632899a2
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3a3e1325f4"
down_revision: Union[str, Sequence[str], None] = "c16a632899a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("courses", sa.Column("learning_goal", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("preferred_level", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_courses_preferred_level",
        "courses",
        "preferred_level IS NULL OR preferred_level IN ('beginner', 'intermediate', 'advanced')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_courses_preferred_level", "courses", type_="check")
    op.drop_column("courses", "preferred_level")
    op.drop_column("courses", "learning_goal")
