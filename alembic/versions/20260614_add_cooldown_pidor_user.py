"""add cooldown pidor user

Revision ID: 20260614_add_cooldown_pidor_user
Revises: 20260614_add_user_is_active
Create Date: 2026-06-14 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_add_cooldown_pidor_user"
down_revision: Union[str, Sequence[str], None] = "20260614_add_user_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cooldowns") as batch_op:
        batch_op.add_column(sa.Column("pidor_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_cooldowns_pidor_user_id_users",
            "users",
            ["pidor_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("cooldowns") as batch_op:
        batch_op.drop_constraint("fk_cooldowns_pidor_user_id_users", type_="foreignkey")
        batch_op.drop_column("pidor_user_id")
