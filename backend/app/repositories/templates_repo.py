from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.templates import NotificationTemplate


class TemplatesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, created_by: uuid.UUID, name: str, subject: str, body: str) -> NotificationTemplate:
        template = NotificationTemplate(name=name, subject=subject, body=body, created_by=created_by)
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get(self, template_id: uuid.UUID) -> NotificationTemplate:
        template = await self.session.get(NotificationTemplate, template_id)
        if not template:
            raise NotFoundError(message="Template not found")
        return template

    async def list(self) -> list[NotificationTemplate]:
        res = await self.session.execute(select(NotificationTemplate).order_by(NotificationTemplate.created_at.desc()))
        return list(res.scalars().all())

    async def update(self, template_id: uuid.UUID, *, name: str, subject: str, body: str) -> NotificationTemplate:
        template = await self.get(template_id)
        template.name = name
        template.subject = subject
        template.body = body
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete(self, template_id: uuid.UUID) -> None:
        template = await self.get(template_id)
        await self.session.delete(template)
        await self.session.commit()

