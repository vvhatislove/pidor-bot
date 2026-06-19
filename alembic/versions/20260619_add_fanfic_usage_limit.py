"""add fanfic usage limit

Revision ID: 20260619_add_fanfic_usage_limit
Revises: 20260616_add_fanfic_messages
Create Date: 2026-06-19 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260619_add_fanfic_usage_limit"
down_revision: Union[str, Sequence[str], None] = "20260616_add_fanfic_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fanfic_usages" not in inspector.get_table_names():
        op.create_table(
            "fanfic_usages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("fanfic_usages")}
    if "ix_fanfic_usages_user_id" not in indexes:
        op.create_index(op.f("ix_fanfic_usages_user_id"), "fanfic_usages", ["user_id"], unique=False)
    if "ix_fanfic_usages_user_created" not in indexes:
        op.create_index("ix_fanfic_usages_user_created", "fanfic_usages", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fanfic_usages" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("fanfic_usages")}
    if "ix_fanfic_usages_user_created" in indexes:
        op.drop_index("ix_fanfic_usages_user_created", table_name="fanfic_usages")
    if "ix_fanfic_usages_user_id" in indexes:
        op.drop_index(op.f("ix_fanfic_usages_user_id"), table_name="fanfic_usages")
    op.drop_table("fanfic_usages")
