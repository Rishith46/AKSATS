"""store extracted resume text

Revision ID: 8f72e91b4c01
Revises: c69358b1a2e
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f72e91b4c01"
down_revision: Union[str, None] = "c69358b1a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_documents", sa.Column("extracted_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_documents", "extracted_text")
