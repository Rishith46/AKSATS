"""make email resume imports idempotent

Revision ID: 4f2ac91d8b30
Revises: 8f72e91b4c01
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f2ac91d8b30"
down_revision: Union[str, None] = "8f72e91b4c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_resume_ingestion_email_attachment", "resume_ingestions", ["email_message_id"])
    op.create_table(
        "gmail_scanned_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=500), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id"),
    )


def downgrade() -> None:
    op.drop_table("gmail_scanned_messages")
    op.drop_constraint(
        "uq_resume_ingestion_email_attachment", "resume_ingestions", type_="unique")
