from __future__ import annotations

import asyncio
import logging
import uuid

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_engine
from app.models.notification_attempts import NotificationAttemptStatus
from app.repositories.notification_attempts_repo import NotificationAttemptsRepository
from app.repositories.notifications_repo import NotificationsRepository
from app.services.metrics_service import metrics
from app.services.notification_worker_service import process_notification
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="notifications.process", max_retries=3)
def process_notification_task(self: Task, notification_id: str, attempt: int = 1) -> None:
    """Celery task entrypoint. Business logic stays in services."""
    nid = uuid.UUID(notification_id)
    logger.info(
        "Notification Processing Started",
        extra={"notification_id": str(nid), "attempt": attempt},
    )

    try:
        # Attempt lifecycle + attempt persistence handled in service.
        process_notification(notification_id=nid, attempt_number=attempt)
        logger.info("Notification Sent", extra={"notification_id": str(nid), "attempt": attempt})
        return
    except Exception as e:
        logger.info(
            "Retry Attempt",
            extra={"notification_id": str(nid), "attempt": attempt, "error": str(e)},
        )

        if attempt >= 3:
            # Dead-letter handling (DB final state)
            engine = get_engine()

            async def runner() -> None:
                sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with sessionmaker() as session:
                    repo = NotificationAttemptsRepository(session)
                    await repo.update_attempt_status(
                        notification_id=nid,
                        attempt_number=attempt,
                        status=NotificationAttemptStatus.FAILED.value,
                        error_message=str(e),
                    )

                    notif_repo = NotificationsRepository(session)
                    await notif_repo.set_status(nid, "FAILED")

            asyncio.run(runner())

            metrics.record_notification_failed(channel="EMAIL", provider="email_provider")

            logger.info(
                "Notification Failed",
                extra={"notification_id": str(nid), "attempt": attempt, "error": str(e)},
            )
            raise

        metrics.record_retry(channel="EMAIL")
        countdown = 0 if attempt == 1 else (30 if attempt == 2 else 60)
        raise self.retry(exc=e, countdown=countdown)
