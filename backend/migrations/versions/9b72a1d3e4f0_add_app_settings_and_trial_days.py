"""add app settings and configurable premium trial days

Revision ID: 9b72a1d3e4f0
Revises: f2a9c44d1b6e
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b72a1d3e4f0"
down_revision: Union[str, Sequence[str], None] = "f2a9c44d1b6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('premium_trial_days', '1')
            ON CONFLICT (key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("app_settings")
