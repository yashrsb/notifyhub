from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_metrics_endpoint_availability(client: AsyncClient) -> None:
    """GET /metrics should return 200 with Prometheus text format."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")
    body = response.text
    # Should contain at least the Prometheus metric headers
    assert "# HELP" in body
    assert "# TYPE" in body


@pytest.mark.anyio
async def test_metrics_registration(client: AsyncClient) -> None:
    """All expected metric names should appear in /metrics output."""
    response = await client.get("/metrics")
    body = response.text

    expected_metrics = [
        "http_requests_total",
        "http_request_duration_seconds",
        "http_response_status_count",
        "notifications_created_total",
        "notifications_sent_total",
        "notifications_failed_total",
        "notification_retries_total",
        "notification_processing_duration_seconds",
        "queue_length",
        "active_workers",
    ]

    for name in expected_metrics:
        assert name in body, f"Metric {name} not found in /metrics output"


@pytest.mark.anyio
async def test_http_request_counter(client: AsyncClient) -> None:
    """After a request, http_requests_total should increment."""
    # Make a request to a known endpoint
    await client.get("/health")
    response = await client.get("/metrics")
    body = response.text

    # Find the http_requests_total line for GET /health with 2xx status
    assert 'http_requests_total{endpoint="/health"' in body
    assert "method=\"GET\"" in body


@pytest.mark.anyio
async def test_http_request_duration_histogram(client: AsyncClient) -> None:
    """After a request, http_request_duration_seconds histogram should exist."""
    await client.get("/health")
    response = await client.get("/metrics")
    body = response.text

    assert "http_request_duration_seconds_bucket" in body
    assert "http_request_duration_seconds_count" in body


@pytest.mark.anyio
async def test_notification_created_counter(client: AsyncClient) -> None:
    """notifications_created_total should be in the output."""
    response = await client.get("/metrics")
    body = response.text

    assert "notifications_created_total" in body
    # Even with no notifications created, the metric should be registered
    # and listed in HELP / TYPE lines


@pytest.mark.anyio
async def test_notification_retries_counter(client: AsyncClient) -> None:
    """notification_retries_total should be registered."""
    response = await client.get("/metrics")
    body = response.text

    assert "notification_retries_total" in body
    assert "# TYPE notification_retries_total counter" in body


@pytest.mark.anyio
async def test_notification_failed_counter(client: AsyncClient) -> None:
    """notifications_failed_total should be registered."""
    response = await client.get("/metrics")
    body = response.text

    assert "notifications_failed_total" in body
    assert "# TYPE notifications_failed_total counter" in body


@pytest.mark.anyio
async def test_processing_duration_histogram(client: AsyncClient) -> None:
    """notification_processing_duration_seconds should be registered."""
    response = await client.get("/metrics")
    body = response.text

    assert "notification_processing_duration_seconds" in body
    assert "histogram" in body


@pytest.mark.anyio
async def test_queue_length_gauge(client: AsyncClient) -> None:
    """queue_length gauge should be registered (best-effort)."""
    response = await client.get("/metrics")
    body = response.text

    assert "queue_length" in body
    assert "# TYPE queue_length gauge" in body


@pytest.mark.anyio
async def test_active_workers_gauge(client: AsyncClient) -> None:
    """active_workers gauge should be registered (best-effort)."""
    response = await client.get("/metrics")
    body = response.text

    assert "active_workers" in body
    assert "# TYPE active_workers gauge" in body


@pytest.mark.anyio
async def test_metrics_disabled_via_config(client_app, client: AsyncClient) -> None:
    """When metrics are disabled, /metrics should return empty output."""
    from app.core.config import settings as app_settings
    from app.services.metrics_service import metrics as metrics_singleton

    original_enabled = app_settings.metrics_enabled
    try:
        app_settings.metrics_enabled = False
        # Recreate registry in disabled state (simulate by calling generate_latest on disabled instance)
        # In test we just verify the singleton's generate_latest handles it
        payload = metrics_singleton.generate_latest()
        assert payload == b"# Metrics disabled\n"
    finally:
        app_settings.metrics_enabled = original_enabled
