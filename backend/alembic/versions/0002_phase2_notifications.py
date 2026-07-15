from __future__ import annotations

import uuid

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from alembic import op


revision = "0002_phase2_notifications"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # notification_attempts table (Phase 2)
    op.create_table(
        "notification_attempts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("notification_id", pg.UUID(as_uuid=True), sa.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notification_attempts_notification_id", "notification_attempts", ["notification_id"])
    op.create_index(
        "ix_notification_attempts_notification_id_attempt_number",
        "notification_attempts",
        ["notification_id", "attempt_number"],
        unique=False,
    )

    # Update notifications.status enum/value semantics by allowing PROCESSING and SENT/FAILED.
    # In Phase 1, notifications.status defaulted to 'pending'.
    # We change it to uppercase strings and include PROCESSING.

    # Alter status column server default
    op.alter_column(
        "notifications",
        "status",
        server_default="PENDING",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_attempts_notification_id_attempt_number", table_name="notification_attempts")
    op.drop_index("ix_notification_attempts_notification_id", table_name="notification_attempts")
    op.drop_table("notification_attempts")

    # Revert to Phase 1 default
    op.alter_column(
        "notifications",
        "status",
        server_default="pending",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )

