from __future__ import annotations

from app.core.config import settings
from app.providers.base import NotificationProvider
from app.providers.email_provider import EmailProvider


class EmailProviderAdapter(NotificationProvider):
    def __init__(self) -> None:
        self._provider = EmailProvider(
            simulation_enabled=settings.email_simulation_enabled,
            failure_rate=settings.email_failure_rate,
        )

    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
    ) -> None:
        # Reuse existing synchronous provider behavior.
        self._provider.send_email(recipient=recipient, subject=subject or "", body=body)

