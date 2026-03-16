"""add generation metadata to courses and lessons

Revision ID: ab4f1c9d2e77
Revises: d7f3b2e1a509
Create Date: 2026-03-16 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab4f1c9d2e77"
down_revision: Union[str, Sequence[str], None] = "d7f3b2e1a509"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("courses", sa.Column("generation_metadata", sa.JSON(), nullable=True))
    op.add_column("lessons", sa.Column("generation_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("lessons", "generation_metadata")
    op.drop_column("courses", "generation_metadata")
