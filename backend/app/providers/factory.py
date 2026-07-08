from __future__ import annotations

import logging
from typing import Final

from app.models.notifications import NotificationChannel
from app.providers.base import NotificationProvider
from app.providers.email_provider_adapter import EmailProviderAdapter
from app.providers.sms_provider import SMSProvider
from app.providers.push_provider import PushProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    _REGISTRY: Final[dict[NotificationChannel, type[NotificationProvider]]] = {
        NotificationChannel.EMAIL: EmailProviderAdapter,
        NotificationChannel.SMS: SMSProvider,
        NotificationChannel.PUSH: PushProvider,
    }

    @classmethod
    def get_provider(cls, channel: NotificationChannel) -> NotificationProvider:
        provider_cls = cls._REGISTRY.get(channel)
        if provider_cls is None:
            raise ValueError(f"Unsupported notification channel: {channel}")
        logger.info("Provider selected", extra={"channel": channel.value})
        return provider_cls()

