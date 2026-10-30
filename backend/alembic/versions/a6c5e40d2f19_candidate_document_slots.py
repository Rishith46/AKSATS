"""add fixed candidate supporting document slots

Revision ID: a6c5e40d2f19
Revises: 4f2ac91d8b30
Create Date: 2026-10-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6c5e40d2f19"
down_revision: Union[str, None] = "4f2ac91d8b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_documents", sa.Column("slot", sa.String(length=30), nullable=True))
    op.add_column("candidate_documents", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.create_unique_constraint(
        "uq_candidate_document_slot",
        "candidate_documents",
        ["candidate_id", "slot"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_candidate_document_slot", "candidate_documents", type_="unique")
    op.drop_column("candidate_documents", "display_name")
    op.drop_column("candidate_documents", "slot")
