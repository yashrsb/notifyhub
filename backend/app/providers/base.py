from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    @abstractmethod
    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
    ) -> None:
        raise NotImplementedError

