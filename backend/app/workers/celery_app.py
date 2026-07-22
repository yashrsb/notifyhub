from __future__ import annotations

import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)


celery_app = Celery(
    "notifyhub",
    broker=settings.redis_broker_url,
    backend=settings.redis_result_backend_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # In tests we may run eager mode.
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
)

# Instrument Celery for OpenTelemetry if tracing is enabled
if settings.otel_enabled:
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
        logger.info("Celery instrumented for OpenTelemetry")
    except Exception as e:
        logger.warning("Failed to instrument Celery for OpenTelemetry", extra={"error": str(e)})
