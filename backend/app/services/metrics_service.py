from __future__ import annotations

import logging
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, disable_creation, registry

from app.core.config import settings

logger = logging.getLogger(__name__)

_metrics_registry = None


class MetricsRegistry:
    """Centralized metrics registry.

    All Prometheus metrics are defined here to prevent duplicate registration
    across application reloads or tests.  The caller should interact only with
    the methods on this class, never with Prometheus internals.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

        if not enabled:
            disable_creation()
            self._reg = None
            logger.info("Metrics collection disabled via configuration")
            return

        self._reg = registry.CollectorRegistry(auto_describe=True)

        # ── HTTP Metrics ──────────────────────────────────────────────
        self.http_requests_total: Counter | None = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            labelnames=["method", "endpoint", "status_code"],
            registry=self._reg,
        )

        self.http_request_duration_seconds: Histogram | None = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency in seconds",
            labelnames=["method", "endpoint"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self._reg,
        )

        self.http_response_status_count: Counter | None = Counter(
            "http_response_status_count",
            "Count of HTTP responses grouped by status code",
            labelnames=["status_code"],
            registry=self._reg,
        )

        # ── Notification Metrics ──────────────────────────────────────
        self.notifications_created_total: Counter | None = Counter(
            "notifications_created_total",
            "Total number of notifications created",
            labelnames=["channel"],
            registry=self._reg,
        )

        self.notifications_sent_total: Counter | None = Counter(
            "notifications_sent_total",
            "Total number of notifications sent successfully",
            labelnames=["channel", "provider"],
            registry=self._reg,
        )

        self.notifications_failed_total: Counter | None = Counter(
            "notifications_failed_total",
            "Total number of notifications that permanently failed",
            labelnames=["channel", "provider"],
            registry=self._reg,
        )

        self.notification_retries_total: Counter | None = Counter(
            "notification_retries_total",
            "Total number of notification retry attempts",
            labelnames=["channel"],
            registry=self._reg,
        )

        self.notification_processing_duration_seconds: Histogram | None = Histogram(
            "notification_processing_duration_seconds",
            "Time taken to process a notification (worker start → provider finish)",
            labelnames=["channel", "provider", "status"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            registry=self._reg,
        )

        # ── Queue Metrics (best-effort) ────────────────────────────────
        self.queue_length: Gauge | None = Gauge(
            "queue_length",
            "Current approximate length of the notification queue in Redis (best-effort)",
            labelnames=["queue_name"],
            registry=self._reg,
        )

        self.active_workers: Gauge | None = Gauge(
            "active_workers",
            "Number of active Celery workers (best-effort, may not be accurate)",
            labelnames=["queue_name"],
            registry=self._reg,
        )

        logger.info("Prometheus metrics registry initialised")

    @property
    def reg(self) -> registry.CollectorRegistry | None:
        return self._reg

    # ── Convenience helpers ───────────────────────────────────────────
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        if not self._enabled or self.http_requests_total is None:
            return
        status_group = str(status_code)[0] + "xx"
        self.http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_group).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        # Use more specific for status_count
        self.http_response_status_count.labels(status_code=str(status_code)).inc()

    def record_notification_created(self, channel: str) -> None:
        if self._enabled and self.notifications_created_total is not None:
            self.notifications_created_total.labels(channel=channel).inc()

    def record_notification_sent(self, channel: str, provider: str, duration: float) -> None:
        if self._enabled and self.notifications_sent_total is not None:
            self.notifications_sent_total.labels(channel=channel, provider=provider).inc()
        if self._enabled and self.notification_processing_duration_seconds is not None:
            self.notification_processing_duration_seconds.labels(
                channel=channel, provider=provider, status="success"
            ).observe(duration)

    def record_notification_failed(self, channel: str, provider: str) -> None:
        if self._enabled and self.notifications_failed_total is not None:
            self.notifications_failed_total.labels(channel=channel, provider=provider).inc()

    def record_retry(self, channel: str) -> None:
        if self._enabled and self.notification_retries_total is not None:
            self.notification_retries_total.labels(channel=channel).inc()

    def record_processing_duration(self, channel: str, provider: str, status: str, duration: float) -> None:
        if self._enabled and self.notification_processing_duration_seconds is not None:
            self.notification_processing_duration_seconds.labels(
                channel=channel, provider=provider, status=status
            ).observe(duration)

    def set_queue_length(self, queue_name: str, length: float) -> None:
        if self._enabled and self.queue_length is not None:
            self.queue_length.labels(queue_name=queue_name).set(length)

    def set_active_workers(self, queue_name: str, count: float) -> None:
        if self._enabled and self.active_workers is not None:
            self.active_workers.labels(queue_name=queue_name).set(count)

    def generate_latest(self) -> bytes:
        """Return the Prometheus text-format payload for the /metrics endpoint."""
        if not self._enabled or self._reg is None:
            return b"# Metrics disabled\n"
        from prometheus_client import generate_latest as _generate_latest

        return _generate_latest(self._reg)


# Module-level singleton – imported by middleware, services, and tasks.
metrics: MetricsRegistry = MetricsRegistry(enabled=settings.metrics_enabled)
