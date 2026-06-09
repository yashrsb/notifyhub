from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from alembic import op

import uuid


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "notification_templates",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notification_templates_created_by", "notification_templates", ["created_by"])

    op.create_table(
        "notifications",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("template_id", pg.UUID(as_uuid=True), sa.ForeignKey("notification_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rendered_subject", sa.Text(), nullable=False),
        sa.Column("rendered_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_template_id", "notifications", ["template_id"])
    op.create_index("ix_notifications_recipient", "notifications", ["recipient"])


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient", table_name="notifications")
    op.drop_index("ix_notifications_template_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_notification_templates_created_by", table_name="notification_templates")
    op.drop_table("notification_templates")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

