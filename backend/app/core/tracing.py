from __future__ import annotations

import logging
import os
import socket

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    HOST_NAME,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def _get_hostname() -> str:
    """Return the system hostname, falling back to 'unknown'."""
    try:
        return socket.gethostname()
    except Exception:
        return os.environ.get("HOSTNAME", "unknown")


def _get_instance_id() -> str:
    """Return a stable instance identifier, falling back to hostname."""
    return os.environ.get("SERVICE_INSTANCE_ID", _get_hostname())


def get_tracer_provider() -> TracerProvider | None:
    """Return the global TracerProvider if tracing is enabled, else None."""
    global _tracer_provider
    return _tracer_provider


def get_tracer(name: str = "notifyhub") -> trace.Tracer:
    """Return the global OpenTelemetry Tracer instance.

    If tracing is disabled (OTEL_ENABLED=false), returns a no-op tracer.
    """
    global _tracer
    if _tracer is not None:
        return _tracer

    if not settings.otel_enabled:
        _tracer = trace.get_tracer(name)
        return _tracer

    provider = _ensure_provider()
    _tracer = provider.get_tracer(name, "1.0.0")
    return _tracer


def _ensure_provider() -> TracerProvider:
    """Create and configure the global TracerProvider if not already done."""
    global _tracer_provider

    if _tracer_provider is not None:
        return _tracer_provider

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_VERSION: settings.service_version,
            DEPLOYMENT_ENVIRONMENT: settings.deployment_environment,
            HOST_NAME: _get_hostname(),
            SERVICE_INSTANCE_ID: _get_instance_id(),
        }
    )

    _tracer_provider = TracerProvider(resource=resource)

    # Always log to console for debugging (can be disabled via exporter config)
    console_exporter = ConsoleSpanExporter()
    _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # If an OTLP endpoint is configured, also export via OTLP
    if settings.otel_exporter_otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                headers=settings.otel_exporter_otlp_headers,
            )
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                "OTLP span exporter configured",
                extra={"endpoint": settings.otel_exporter_otlp_endpoint},
            )
        except Exception as e:
            logger.warning(
                "Failed to configure OTLP exporter, proceeding with console only",
                extra={"error": str(e)},
            )

    trace.set_tracer_provider(_tracer_provider)
    logger.info(
        "OpenTelemetry tracer provider initialised",
        extra={
            "service_name": settings.otel_service_name,
            "service_version": settings.service_version,
            "deployment_environment": settings.deployment_environment,
        },
    )
    return _tracer_provider


def shutdown_tracing() -> None:
    """Gracefully shut down the trace provider, flushing remaining spans."""
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None
        _tracer = None
        logger.info("OpenTelemetry tracer provider shut down")
