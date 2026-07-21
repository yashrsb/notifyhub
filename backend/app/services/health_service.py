from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DependencyCheckResult:
    database: bool
    redis: bool
    celery: str


class HealthService:
    def __init__(self, *, session: AsyncSession | None = None) -> None:
        # Session is optional so /health can remain ultra-light.
        self._session = session

    async def check_ready(self) -> DependencyCheckResult:
        if not getattr(settings, "healthcheck_enabled", True):
            # If health checks are disabled, treat everything as not_ready (operator can gate this).
            return DependencyCheckResult(database=False, redis=False, celery="not_checked")

        database_ok = await self._check_database() if getattr(settings, "readiness_check_database", True) else True
        redis_ok = await self._check_redis() if getattr(settings, "readiness_check_redis", True) else True

        celery_check = "not_checked"
        # Celery is optional per requirements.
        if getattr(settings, "readiness_check_celery", False):
            # No reliable lightweight celery connectivity check in this phase.
            celery_check = "not_checked"

        return DependencyCheckResult(database=database_ok, redis=redis_ok, celery=celery_check)

    async def _check_database(self) -> bool:
        if self._session is None:
            return False

        try:
            await self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.warning(
                "Database connectivity check failed",
                extra={"error": "exception"},
            )
            return False

    async def _check_redis(self) -> bool:
        redis_client = getattr(settings, "_rate_limit_redis", None)
        if redis_client is None:
            # Fallback: no Redis client configured lazily.
            try:
                from redis.asyncio import Redis as AsyncRedis

                redis_client = AsyncRedis.from_url(settings.redis_broker_url, decode_responses=False)
            except Exception:
                return False

        try:
            # PING is fast.
            await redis_client.ping()
            return True
        except Exception:
            return False

