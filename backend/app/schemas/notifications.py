from __future__ import annotations

import uuid
from enum import Enum

from app.models.notifications import NotificationChannel

from typing import Any

from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationCreateRequest(BaseModel):
    channel: "NotificationChannel" = Field(min_length=1, max_length=64)

    @staticmethod
    def _normalize_channel(v: Any) -> Any:
        if isinstance(v, str):
            v_upper = v.upper()
            if v_upper in {"EMAIL", "SMS", "PUSH"}:
                return v_upper
        return v

    @classmethod
    def model_validate(cls, obj: Any, *, strict: bool | None = None):  # type: ignore[override]
        if isinstance(obj, dict) and "channel" in obj:
            obj = dict(obj)
            obj["channel"] = cls._normalize_channel(obj["channel"])
        return super().model_validate(obj, strict=strict)

    recipient: str
    template_id: uuid.UUID
    variables: dict[str, Any] = {}


class NotificationAttemptResponse(BaseModel):
    attempt: int
    status: str
    error: str | None = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    # channel stored as string/enum in DB, returned as-is

    channel: str
    recipient: str
    template_id: uuid.UUID
    rendered_subject: str
    rendered_body: str

    status: NotificationStatus
    created_at: str
    attempts: list[NotificationAttemptResponse] = []


class NotificationQueuedResponse(BaseModel):
    success: bool = True
    message: str = "Notification queued"
    notification_id: uuid.UUID

