from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.db.base import Base, TimestampMixin


class NotificationAttemptStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class NotificationAttempt(Base, TimestampMixin):
    __tablename__ = "notification_attempts"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[NotificationAttemptStatus] = mapped_column(String(length=32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)

    notification: Mapped["Notification"] = relationship(
        "Notification",
        back_populates="attempts",
    )


