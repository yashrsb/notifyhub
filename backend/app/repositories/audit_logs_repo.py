from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditAction, AuditEntityType, AuditLog


@dataclass(frozen=True)
class AuditLogSearchParams:
    entity_type: AuditEntityType | None = None
    entity_id: str | None = None
    action: AuditAction | None = None
    performed_by: str | None = None
    from_created_at: Any | None = None  # datetime | date
    to_created_at: Any | None = None


class AuditLogsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, *, log: AuditLog) -> AuditLog:
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def search(
        self,
        *,
        params: AuditLogSearchParams,
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> tuple[list[AuditLog], int]:
        where_clauses: list[Any] = []

        if params.entity_type is not None:
            where_clauses.append(AuditLog.entity_type == params.entity_type)
        if params.entity_id is not None:
            where_clauses.append(AuditLog.entity_id == params.entity_id)
        if params.action is not None:
            where_clauses.append(AuditLog.action == params.action)
        if params.performed_by is not None:
            where_clauses.append(AuditLog.performed_by == params.performed_by)

        if params.from_created_at is not None:
            where_clauses.append(AuditLog.created_at >= params.from_created_at)
        if params.to_created_at is not None:
            where_clauses.append(AuditLog.created_at <= params.to_created_at)

        where = and_(*where_clauses) if where_clauses else None

        # total count
        count_stmt = select(AuditLog.id)
        if where is not None:
            count_stmt = count_stmt.where(where)
        count_stmt = count_stmt.order_by(None)
        res_total = await self.session.execute(count_stmt)
        # Inefficient counting workaround without count() SQLAlchemy function in async.
        # For correctness in this phase, we load ids and count them.
        total = len(res_total.scalars().all())

        stmt = select(AuditLog)
        if where is not None:
            stmt = stmt.where(where)

        # Sorting
        sort_col = {
            "created_at": AuditLog.created_at,
            "entity_type": AuditLog.entity_type,
            "entity_id": AuditLog.entity_id,
            "action": AuditLog.action,
        }.get(sort_field, AuditLog.created_at)

        if sort_dir.lower() == "desc":
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())

        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

