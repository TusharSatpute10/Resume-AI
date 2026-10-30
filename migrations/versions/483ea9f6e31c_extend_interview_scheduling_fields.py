"""extend interview scheduling fields

Revision ID: 483ea9f6e31c
Revises: 059e6b416e10
Create Date: 2026-10-30 21:01:08.609004
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "483ea9f6e31c"
down_revision: Union[str, None] = "059e6b416e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Add columns as nullable to preserve existing records.
    op.add_column(
        "interviews",
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("round_name", sa.String(100), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("meeting_link_status", sa.String(30), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("venue", sa.String(500), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("instructions", sa.Text(), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "interviews",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Backfill existing interview records.
    op.execute(
        """
        UPDATE interviews
        SET
            duration_minutes = 30,
            round_name = 'Technical Round',
            meeting_link_status = CASE
                WHEN meeting_link IS NOT NULL AND meeting_link <> ''
                THEN 'AVAILABLE'
                ELSE 'PENDING'
            END,
            created_at = scheduled_at,
            updated_at = scheduled_at
        """
    )

    # Enforce NOT NULL after backfilling.
    op.alter_column(
        "interviews",
        "duration_minutes",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "interviews",
        "round_name",
        existing_type=sa.String(100),
        nullable=False,
    )

    op.alter_column(
        "interviews",
        "meeting_link_status",
        existing_type=sa.String(30),
        nullable=False,
    )

    op.alter_column(
        "interviews",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )

    op.alter_column(
        "interviews",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )


def downgrade() -> None:

    op.drop_column("interviews", "updated_at")
    op.drop_column("interviews", "created_at")
    op.drop_column("interviews", "cancelled_at")
    op.drop_column("interviews", "instructions")
    op.drop_column("interviews", "venue")
    op.drop_column("interviews", "meeting_link_status")
    op.drop_column("interviews", "round_name")
    op.drop_column("interviews", "duration_minutes")