from __future__ import annotations

import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_attempts import NotificationAttempt, NotificationAttemptStatus


class NotificationAttemptsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_attempt(
        self,
        *,
        notification_id: uuid.UUID,
        attempt_number: int,
        status: str,
        error_message: str | None,
    ) -> NotificationAttempt:
        attempt = NotificationAttempt(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=status,
            error_message=error_message,
        )
        self.session.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)
        return attempt


    async def list_by_notification_id(self, notification_id: uuid.UUID) -> list[NotificationAttempt]:
        res = await self.session.execute(
            select(NotificationAttempt).where(NotificationAttempt.notification_id == notification_id).order_by(
                NotificationAttempt.attempt_number.asc()
            )
        )
        return list(res.scalars().all())

    async def update_attempt_status(
        self,
        *,
        notification_id: uuid.UUID,
        attempt_number: int,
        status: str,
        error_message: str | None,
    ) -> None:
        await self.session.execute(
            select(NotificationAttempt)
        )
        attempt = (
            await self.session.execute(
                select(NotificationAttempt).where(
                    and_(
                        NotificationAttempt.notification_id == notification_id,
                        NotificationAttempt.attempt_number == attempt_number,
                    )
                )
            )
        ).scalar_one_or_none()

        if not attempt:
            # If the attempt row doesn't exist, create it as failed.
            await self.create_attempt(
                notification_id=notification_id,
                attempt_number=attempt_number,
                status=status,
                error_message=error_message,
            )
            return

        attempt.status = status
        attempt.error_message = error_message
        await self.session.commit()

