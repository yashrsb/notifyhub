from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.idempotency_keys import IdempotencyKey


class IdempotencyKeysRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, *, key: str) -> IdempotencyKey | None:
        res = await self.session.execute(select(IdempotencyKey).where(IdempotencyKey.key == key))
        return res.scalars().first()

    async def create(
        self,
        *,
        key: str,
        request_hash: str,
        notification_id: uuid.UUID,
        response_body: dict[str, Any],
        status_code: int,
        expires_at,
    ) -> IdempotencyKey:
        row = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            notification_id=notification_id,
            response_body=response_body,
            status_code=status_code,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

