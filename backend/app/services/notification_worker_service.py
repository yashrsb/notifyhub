from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.session import get_engine
from app.models.notification_attempts import NotificationAttemptStatus
from app.models.notifications import NotificationStatus
from app.providers.email_provider import EmailProvider
from app.repositories.notification_attempts_repo import NotificationAttemptsRepository
from app.repositories.notifications_repo import NotificationsRepository
from app.repositories.templates_repo import TemplatesRepository
from app.utils.template_renderer import render_template_text

logger = logging.getLogger(__name__)


async def _process_notification_async(
    *,
    session: AsyncSession,
    notification_id: uuid.UUID,
    attempt_number: int,
) -> None:
    notif_repo = NotificationsRepository(session)
    attempt_repo = NotificationAttemptsRepository(session)

    notif = await notif_repo.get(notification_id)
    if not notif:
        raise NotFoundError(message="Notification not found")

    # Worker picked up
    await notif_repo.set_status(notification_id, NotificationStatus.PROCESSING.value)

    provider = EmailProvider(
        simulation_enabled=settings.email_simulation_enabled,
        failure_rate=settings.email_failure_rate,
    )

    # Every attempt must be persisted
    try:
        await attempt_repo.create_attempt(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.PENDING.value,
            error_message=None,
        )

        tpl_repo = TemplatesRepository(session)
        tpl = await tpl_repo.get(notif.template_id)

        rendered_subject = render_template_text(tpl.subject, {})
        rendered_body = render_template_text(tpl.body, {})

        provider.send_email(
            recipient=notif.recipient,
            subject=rendered_subject,
            body=rendered_body,
        )

        await attempt_repo.update_attempt_status(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.SUCCESS.value,
            error_message=None,
        )
        await notif_repo.set_status(notification_id, NotificationStatus.SENT.value)

    except Exception as e:
        await attempt_repo.update_attempt_status(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.FAILED.value,
            error_message=str(e),
        )
        # Notification error is considered dead-letter “final error”; we store it in attempts.
        # Keep set_last_error as a no-op (schema compatible).
        await notif_repo.set_last_error(notification_id, str(e))
        raise


def process_notification(*, notification_id: uuid.UUID, attempt_number: int) -> None:
    """Synchronous wrapper so Celery can call it."""
    import asyncio

    async def runner() -> None:
        engine = get_engine()
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with sessionmaker() as session:
            await _process_notification_async(
                session=session,
                notification_id=notification_id,
                attempt_number=attempt_number,
            )

    asyncio.run(runner())


async def get_notification_with_attempts(
    *,
    session: AsyncSession,
    notification_id: uuid.UUID | None = None,
):
    notif_repo = NotificationsRepository(session)
    attempt_repo = NotificationAttemptsRepository(session)

    if notification_id is not None:
        notif = await notif_repo.get(notification_id)
        if not notif:
            raise NotFoundError(message="Notification not found")

        attempts = await attempt_repo.list_by_notification_id(notification_id)
        notif.attempts = [
            {
                "attempt": a.attempt_number,
                "status": "FAILED" if a.status == NotificationAttemptStatus.FAILED.value else "SUCCESS",
                "error": a.error_message,
            }
            for a in attempts
        ]
        return notif

    notifs = await notif_repo.list()
    # Attach attempts for each notification (best effort)
    for n in notifs:
        attempts = await attempt_repo.list_by_notification_id(n.id)
        n.attempts = [
            {
                "attempt": a.attempt_number,
                "status": "FAILED" if a.status == NotificationAttemptStatus.FAILED.value else "SUCCESS",
                "error": a.error_message,
            }
            for a in attempts
        ]
    return notifs

