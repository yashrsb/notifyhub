from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.session import get_engine
from app.models.notification_attempts import NotificationAttemptStatus
from app.models.notifications import NotificationChannel, NotificationStatus
from app.providers.factory import ProviderFactory


from app.repositories.notification_attempts_repo import NotificationAttemptsRepository
from app.repositories.notifications_repo import NotificationsRepository
from app.repositories.templates_repo import TemplatesRepository
from app.services.metrics_service import metrics
from app.utils.template_renderer import render_template_text

logger = logging.getLogger(__name__)

PROVIDER_NAME_MAP: dict[str, str] = {
    "EMAIL": "email_provider",
    "SMS": "sms_provider",
    "PUSH": "push_provider",
}


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

    # Select provider via factory (worker is decoupled from implementations)
    channel_enum = NotificationChannel(notif.channel)
    provider = ProviderFactory.get_provider(channel_enum)

    provider_name = PROVIDER_NAME_MAP.get(notif.channel, "unknown")

    # Every attempt must be persisted
    start_time = time.monotonic()

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

        await provider.send(
            recipient=notif.recipient,
            subject=rendered_subject,
            body=rendered_body,
        )

        duration = time.monotonic() - start_time

        await attempt_repo.update_attempt_status(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.SUCCESS.value,
            error_message=None,
        )
        await notif_repo.set_status(notification_id, NotificationStatus.SENT.value)

        metrics.record_notification_sent(channel=notif.channel, provider=provider_name, duration=duration)

    except Exception as e:
        duration = time.monotonic() - start_time

        await attempt_repo.update_attempt_status(
            notification_id=notification_id,
            attempt_number=attempt_number,
            status=NotificationAttemptStatus.FAILED.value,
            error_message=str(e),
        )

        metrics.record_processing_duration(
            channel=notif.channel, provider=provider_name, status="failed", duration=duration
        )
        # Notification error is considered dead-letter "final error"; we store it in attempts.
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

        return notif

    return await notif_repo.list()
