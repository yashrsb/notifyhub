from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.notifications import Notification
from app.models.templates import NotificationTemplate
from app.repositories.notifications_repo import NotificationsRepository
from app.utils.template_renderer import render_template_text


async def create_notification(
    *,
    session: AsyncSession,
    channel: str,
    recipient: str,
    template_id: uuid.UUID,
    variables: dict[str, object],
) -> Notification:
    tpl = await session.get(NotificationTemplate, template_id)
    if not tpl:
        raise NotFoundError(message="Template not found")

    rendered_subject = render_template_text(tpl.subject, variables)
    rendered_body = render_template_text(tpl.body, variables)

    repo = NotificationsRepository(session)
    return await repo.create(
        channel=channel,
        recipient=recipient,
        template_id=template_id,
        rendered_subject=rendered_subject,
        rendered_body=rendered_body,
    )


async def list_notifications(*, session: AsyncSession):
    repo = NotificationsRepository(session)
    return await repo.list()


async def get_notification(*, session: AsyncSession, notification_id: uuid.UUID) -> Notification:
    repo = NotificationsRepository(session)
    notif = await repo.get(notification_id)
    if not notif:
        raise NotFoundError(message="Notification not found")
    return notif

