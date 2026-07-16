from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base, TimestampMixin


class AuditEntityType(StrEnum):
    USER = "USER"
    NOTIFICATION = "NOTIFICATION"
    TEMPLATE = "TEMPLATE"
    SYSTEM = "SYSTEM"
    PROVIDER = "PROVIDER"
    WORKER = "WORKER"


class AuditAction(StrEnum):
    # Auth
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGGED_IN = "USER_LOGGED_IN"

    # Notifications
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"
    NOTIFICATION_QUEUED = "NOTIFICATION_QUEUED"
    NOTIFICATION_PROCESSING_STARTED = "NOTIFICATION_PROCESSING_STARTED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    NOTIFICATION_RETRY_SCHEDULED = "NOTIFICATION_RETRY_SCHEDULED"

    # Templates
    TEMPLATE_CREATED = "TEMPLATE_CREATED"
    TEMPLATE_UPDATED = "TEMPLATE_UPDATED"
    TEMPLATE_DELETED = "TEMPLATE_DELETED"


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entity_type: Mapped[AuditEntityType] = mapped_column(
        String(length=64), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(String(length=64), nullable=True, index=True)

    action: Mapped[AuditAction] = mapped_column(String(length=128), nullable=False, index=True)

    performed_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)


    metadata: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)

    created_at: Mapped[object] = mapped_column(
        # Override to keep TimestampMixin fields but ensure correct indexing in migrations.
        # TimestampMixin already defines created_at; we keep it.
        # This placeholder is never used by SQLAlchemy directly.
        init=False,
    )

