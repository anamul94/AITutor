"""add language to courses

Revision ID: f2a9c44d1b6e
Revises: e4f9c7a2b1d0
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a9c44d1b6e"
down_revision: Union[str, Sequence[str], None] = "e4f9c7a2b1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("language", sa.String(length=20), nullable=False, server_default=sa.text("'english'")),
    )
    op.create_check_constraint(
        "ck_courses_language",
        "courses",
        "language IN ('english', 'bengali', 'hindi')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_courses_language", "courses", type_="check")
    op.drop_column("courses", "language")
