"""add description to lessons

Revision ID: b5f2e4d9a731
Revises: 8f3a3e1325f4
Create Date: 2026-02-28 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5f2e4d9a731"
down_revision: Union[str, Sequence[str], None] = "8f3a3e1325f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("lessons", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("lessons", "description")
