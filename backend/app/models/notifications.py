from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.db.base import Base, TimestampMixin


class NotificationChannel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"



class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[NotificationChannel] = mapped_column(String(length=64), nullable=False)

    recipient: Mapped[str] = mapped_column(Text(), nullable=False)

    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )

    rendered_subject: Mapped[str] = mapped_column(Text(), nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text(), nullable=False)

    status: Mapped[NotificationStatus] = mapped_column(
        String(length=32),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default="PENDING",
    )

    attempts: Mapped[list["NotificationAttempt"]] = relationship(
        "NotificationAttempt",
        back_populates="notification",
        cascade="all, delete-orphan",
        order_by="NotificationAttempt.attempt_number",
        lazy="selectin",
    )


