"""expand dsa topic check constraint to include all topics

Revision ID: c4e8a1f2d093
Revises: b2d95d7409f6
Create Date: 2026-03-13 00:00:04.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e8a1f2d093"
down_revision: Union[str, Sequence[str], None] = "b2d95d7409f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALL_TOPICS = (
    "'arrays', 'linked_lists', 'stacks_and_queues', 'sliding_window', 'two_pointers', "
    "'binary_search', 'sorting', 'hashing', 'trees', 'binary_search_tree', 'heaps', "
    "'graphs', 'recursion', 'backtracking', 'dynamic_programming', 'greedy', 'tries', "
    "'bit_manipulation', 'string_manipulation', 'intervals', 'matrix', "
    "'general_problem_solving'"
)

_OLD_TOPICS = (
    "'arrays', 'sliding_window', 'binary_search', 'graphs', 'recursion', "
    "'dynamic_programming', 'general_problem_solving'"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_dsa_coach_sessions_topic",
        "dsa_coach_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_dsa_coach_sessions_topic",
        "dsa_coach_sessions",
        f"topic IN ({_ALL_TOPICS})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_dsa_coach_sessions_topic",
        "dsa_coach_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_dsa_coach_sessions_topic",
        "dsa_coach_sessions",
        f"topic IN ({_OLD_TOPICS})",
    )
