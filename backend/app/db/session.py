from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

        # Instrument engine for OpenTelemetry if tracing is enabled
        if settings.otel_enabled:
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

                SQLAlchemyInstrumentor().instrument(engine=_engine.sync_engine)
                logger.info("SQLAlchemy engine instrumented for OpenTelemetry")
            except Exception as e:
                logger.warning(
                    "Failed to instrument SQLAlchemy for OpenTelemetry",
                    extra={"error": str(e)},
                )

    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session
