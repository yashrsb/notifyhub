from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditAction, AuditEntityType, AuditLog
from app.repositories.audit_logs_repo import AuditLogsRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogsRepository(session)

    async def publish(
        self,
        *,
        entity_type: AuditEntityType,
        entity_id: str | None,
        action: AuditAction,
        performed_by: str | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            meta: dict[str, Any] = dict(metadata) if metadata is not None else {}
            log = AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                performed_by=performed_by,
                metadata=meta,
            )
            await self._repo.insert(log=log)
        except Exception:
            # Audit logging should never break business operations.
            logger.exception(
                "Audit log persistence failed",
                extra={
                    "entity_type": str(entity_type),
                    "entity_id": entity_id,
                    "action": str(action),
                },
            )
            return

