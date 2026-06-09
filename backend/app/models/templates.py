from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text

from app.db.base import Base, TimestampMixin


class NotificationTemplate(Base, TimestampMixin):
    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    subject: Mapped[str] = mapped_column(Text(), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)

    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


