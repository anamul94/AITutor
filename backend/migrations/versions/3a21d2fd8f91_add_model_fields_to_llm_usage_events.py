"""add model fields to llm usage events

Revision ID: 3a21d2fd8f91
Revises: 9b72a1d3e4f0
Create Date: 2026-03-05 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a21d2fd8f91"
down_revision: Union[str, Sequence[str], None] = "9b72a1d3e4f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("llm_usage_events", sa.Column("model_name", sa.String(length=255), nullable=True))
    op.add_column("llm_usage_events", sa.Column("model_provider", sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("llm_usage_events", "model_provider")
    op.drop_column("llm_usage_events", "model_name")
