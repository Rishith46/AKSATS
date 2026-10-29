"""add skill review status

Revision ID: c69358b1a2e
Revises: 1775237f72f1
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c69358b1a2e"
down_revision: Union[str, None] = "1775237f72f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("skills", "needs_review")
