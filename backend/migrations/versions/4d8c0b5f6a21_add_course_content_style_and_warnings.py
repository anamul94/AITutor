"""add content style and warnings to courses

Revision ID: 4d8c0b5f6a21
Revises: d7f3b2e1a509
Create Date: 2026-03-13 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d8c0b5f6a21"
down_revision: Union[str, Sequence[str], None] = "d7f3b2e1a509"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column(
            "content_style",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'balanced'"),
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "generation_warnings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.create_check_constraint(
        "ck_courses_content_style",
        "courses",
        "content_style IN ('conceptual', 'balanced', 'practical')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_courses_content_style", "courses", type_="check")
    op.drop_column("courses", "generation_warnings")
    op.drop_column("courses", "content_style")
