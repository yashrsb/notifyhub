from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit_logs import AuditAction, AuditEntityType
from app.schemas.audit_logs import AuditLogsResponse, AuditLogItem
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    entity_type: AuditEntityType | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    performed_by: str | None = Query(default=None),
    from_: Any | None = Query(default=None, alias="from"),
    to: Any | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    session: AsyncSession = Depends(get_db),
):
    audit_service = AuditService(session=session)

    # Repository access for search parameters (service currently only supports publish).
    # Use repository directly for read to keep publish path audit-safe.
    from app.repositories.audit_logs_repo import AuditLogSearchParams
    from app.repositories.audit_logs_repo import AuditLogsRepository

    repo = AuditLogsRepository(session)

    items, total = await repo.search(
        params=AuditLogSearchParams(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=performed_by,
            from_created_at=from_,
            to_created_at=to,
        ),
        page=page,
        page_size=page_size,
        sort_field=sort,
        sort_dir=sort_dir,
    )

    # Serialize.
    resp_items: list[AuditLogItem] = [
        AuditLogItem(
            id=log.id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            performed_by=log.performed_by,
            metadata=log.metadata or {},
            created_at=str(log.created_at),
        )
        for log in items
    ]

    return AuditLogsResponse(items=resp_items, total=total, page=page, page_size=page_size)

