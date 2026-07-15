from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.audit_logs import AuditAction, AuditEntityType


class AuditLogItem(BaseModel):
    id: uuid.UUID
    entity_type: AuditEntityType
    entity_id: str | None
    action: AuditAction
    performed_by: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AuditLogsResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int

