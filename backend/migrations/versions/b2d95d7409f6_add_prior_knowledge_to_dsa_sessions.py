"""add prior knowledge to dsa sessions

Revision ID: b2d95d7409f6
Revises: 91f3c2ab4e11
Create Date: 2026-03-13 00:40:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2d95d7409f6"
down_revision: Union[str, Sequence[str], None] = "91f3c2ab4e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("dsa_coach_sessions", sa.Column("prior_knowledge", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("dsa_coach_sessions", "prior_knowledge")
