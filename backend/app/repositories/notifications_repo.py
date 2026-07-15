from __future__ import annotations


import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.notifications import Notification


class NotificationsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        channel: str,
        recipient: str,
        template_id,
        rendered_subject: str,
        rendered_body: str,
    ) -> Notification:
        notif = Notification(
            channel=channel,
            recipient=recipient,
            template_id=template_id,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
        )
        self.session.add(notif)
        await self.session.commit()
        await self.session.refresh(notif)
        return notif

    async def list(self) -> list[Notification]:
        res = await self.session.execute(select(Notification).order_by(Notification.created_at.desc()))
        return list(res.scalars().all())

    async def get(self, notification_id):
        return await self.session.get(Notification, notification_id)

    async def set_status(self, notification_id: uuid.UUID, status: str) -> None:
        notif = await self.session.get(Notification, notification_id)

        if notif is None:
            return
        notif.status = status
        await self.session.commit()





