"""bot nation battles

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "defender_kind IN ('player', 'pirate', 'boss')"
NEW = "defender_kind IN ('player', 'pirate', 'boss', 'bot')"


def upgrade() -> None:
    # SQLite can't alter a CHECK constraint, so batch mode rebuilds the table.
    with op.batch_alter_table("battles", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("defender_bot", sa.String(length=64), nullable=True))
        batch_op.drop_constraint(op.f("ck_battles_defender_kind_valid"), type_="check")
        batch_op.create_check_constraint("defender_kind_valid", NEW)
        batch_op.create_index(
            "ix_battles_bot", ["attacker_id", "defender_bot", "created_at"], unique=False
        )


def downgrade() -> None:
    op.execute("DELETE FROM battles WHERE defender_kind = 'bot'")
    with op.batch_alter_table("battles", recreate="always") as batch_op:
        batch_op.drop_index("ix_battles_bot")
        batch_op.drop_constraint(op.f("ck_battles_defender_kind_valid"), type_="check")
        batch_op.create_check_constraint("defender_kind_valid", OLD)
        batch_op.drop_column("defender_bot")
