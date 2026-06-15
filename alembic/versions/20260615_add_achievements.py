"""add achievements

Revision ID: 20260615_add_achievements
Revises: 20260614_add_cooldown_pidor_user
Create Date: 2026-06-15 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_add_achievements"
down_revision: Union[str, Sequence[str], None] = "20260614_add_cooldown_pidor_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("reward_amount", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_achievement_unique", "user_achievements", ["user_id", "achievement_id"], unique=True)
    op.create_index(op.f("ix_user_achievements_achievement_id"), "user_achievements", ["achievement_id"], unique=False)
    op.create_index(op.f("ix_user_achievements_user_id"), "user_achievements", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_achievements_user_id"), table_name="user_achievements")
    op.drop_index(op.f("ix_user_achievements_achievement_id"), table_name="user_achievements")
    op.drop_index("ix_user_achievement_unique", table_name="user_achievements")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
