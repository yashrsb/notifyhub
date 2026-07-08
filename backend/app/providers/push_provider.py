from __future__ import annotations

import logging
import random

from app.core.config import settings
from app.providers.base import NotificationProvider

logger = logging.getLogger(__name__)


class PushProvider(NotificationProvider):
    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
    ) -> None:
        if not settings.email_simulation_enabled:
            logger.info("Push sent", extra={"recipient": recipient})
            return

        if random.random() < settings.email_failure_rate:
            raise Exception("Provider failure")

        logger.info("Push sent", extra={"recipient": recipient})

