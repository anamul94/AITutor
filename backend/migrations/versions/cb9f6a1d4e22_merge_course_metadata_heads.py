"""merge course metadata heads

Revision ID: cb9f6a1d4e22
Revises: 4d8c0b5f6a21, ab4f1c9d2e77
Create Date: 2026-03-16 00:10:01.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "cb9f6a1d4e22"
down_revision: Union[str, Sequence[str], None] = ("4d8c0b5f6a21", "ab4f1c9d2e77")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
