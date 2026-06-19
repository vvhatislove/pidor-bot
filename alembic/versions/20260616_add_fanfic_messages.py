"""add fanfic messages

Revision ID: 20260616_add_fanfic_messages
Revises: 20260615_add_achievements
Create Date: 2026-06-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260616_add_fanfic_messages"
down_revision: Union[str, Sequence[str], None] = "20260615_add_achievements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "fanfic_allowed" not in user_columns:
        op.add_column(
            "users",
            sa.Column("fanfic_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
        )

    if "fanfic_messages" not in inspector.get_table_names():
        op.create_table(
            "fanfic_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "content_hash", name="uq_fanfic_message_user_hash"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("fanfic_messages")}
    if "ix_fanfic_messages_user_id" not in indexes:
        op.create_index(op.f("ix_fanfic_messages_user_id"), "fanfic_messages", ["user_id"], unique=False)
    if "ix_fanfic_messages_user_created" not in indexes:
        op.create_index("ix_fanfic_messages_user_created", "fanfic_messages", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fanfic_messages" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("fanfic_messages")}
        if "ix_fanfic_messages_user_created" in indexes:
            op.drop_index("ix_fanfic_messages_user_created", table_name="fanfic_messages")
        if "ix_fanfic_messages_user_id" in indexes:
            op.drop_index(op.f("ix_fanfic_messages_user_id"), table_name="fanfic_messages")
        op.drop_table("fanfic_messages")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "fanfic_allowed" in user_columns:
        op.drop_column("users", "fanfic_allowed")
