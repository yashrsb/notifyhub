from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationCreateRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=64)
    recipient: str
    template_id: uuid.UUID
    variables: dict[str, Any] = {}


class NotificationAttemptResponse(BaseModel):
    attempt: int
    status: str
    error: str | None = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
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

