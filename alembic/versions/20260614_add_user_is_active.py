"""add user is_active

Revision ID: 20260614_add_user_is_active
Revises: adc142fcd221
Create Date: 2026-06-14 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_add_user_is_active"
down_revision: Union[str, Sequence[str], None] = "adc142fcd221"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
