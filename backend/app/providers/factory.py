from __future__ import annotations

import logging
from typing import Final

from opentelemetry import trace

from app.core.config import settings
from app.models.notifications import NotificationChannel
from app.providers.base import NotificationProvider
from app.providers.email_provider_adapter import EmailProviderAdapter
from app.providers.sms_provider import SMSProvider
from app.providers.push_provider import PushProvider

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("notifyhub.providers")


class ProviderFactory:
    _REGISTRY: Final[dict[NotificationChannel, type[NotificationProvider]]] = {
        NotificationChannel.EMAIL: EmailProviderAdapter,
        NotificationChannel.SMS: SMSProvider,
        NotificationChannel.PUSH: PushProvider,
    }

    _PROVIDER_NAMES: Final[dict[NotificationChannel, str]] = {
        NotificationChannel.EMAIL: "EmailProviderAdapter",
        NotificationChannel.SMS: "SMSProvider",
        NotificationChannel.PUSH: "PushProvider",
    }

    @classmethod
    def get_provider(cls, channel: NotificationChannel) -> NotificationProvider:
        provider_cls = cls._REGISTRY.get(channel)
        if provider_cls is None:
            raise ValueError(f"Unsupported notification channel: {channel}")

        provider_name = cls._PROVIDER_NAMES.get(channel, provider_cls.__name__)

        if settings.otel_enabled:
            with tracer.start_as_current_span("Provider.Resolve") as span:
                span.set_attribute("provider.name", provider_name)
                span.set_attribute("provider.channel", channel.value)

        logger.info("Provider selected", extra={"channel": channel.value, "provider": provider_name})
        return provider_cls()
