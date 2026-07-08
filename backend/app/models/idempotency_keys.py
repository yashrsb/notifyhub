from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IdempotencyStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(length=256), nullable=False, unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(length=64), nullable=False)

    notification_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    response_body: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    expires_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

