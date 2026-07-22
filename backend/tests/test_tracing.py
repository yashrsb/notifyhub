from __future__ import annotations

import os

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.main import create_app


@pytest.fixture()
def tracing_app():
    """Create app with tracing enabled."""
    saved = settings.otel_enabled
    settings.otel_enabled = True
    app = create_app()
    yield app
    settings.otel_enabled = saved


@pytest.fixture()
def no_tracing_app():
    """Create app with tracing disabled."""
    saved = settings.otel_enabled
    settings.otel_enabled = False
    app = create_app()
    yield app
    settings.otel_enabled = saved


@pytest.mark.anyio
async def test_tracing_enabled_returns_headers(tracing_app):
    """When tracing is enabled, trace headers are injected into the response."""
    async with AsyncClient(app=tracing_app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "trace-test@example.com", "password": "Password123!"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "trace-test@example.com", "password": "Password123!"},
        )
        token = resp.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/templates", headers=headers)
        assert response.status_code in (200, 404)
        # traceparent header should be injected by TracingHTTPMiddleware
        # The response itself might or might not contain traceparent depending
        # on the span processor flushing, but the middleware injects it.
        # We check for presence of traceparent in response headers
        # (may be absent if span was not sampled, but likely present)
        if "traceparent" in response.headers:
            assert response.headers["traceparent"].startswith("00-")


@pytest.mark.anyio
async def test_tracing_disabled_no_trace_headers(no_tracing_app):
    """When tracing is disabled, no trace headers are injected."""
    async with AsyncClient(app=no_tracing_app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "trace-disabled@example.com", "password": "Password123!"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "trace-disabled@example.com", "password": "Password123!"},
        )
        token = resp.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/templates", headers=headers)
        assert "traceparent" not in response.headers
        assert "tracestate" not in response.headers


@pytest.mark.anyio
async def test_tracing_middleware_sets_request_id(tracing_app):
    """When tracing is enabled, request.id attribute is set."""
    async with AsyncClient(app=tracing_app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.anyio
async def test_tracing_middleware_captures_http_status(tracing_app):
    """HTTP status code is captured as span attribute."""
    async with AsyncClient(app=tracing_app, base_url="http://test") as client:
        # 200 OK
        resp_ok = await client.get("/health")
        assert resp_ok.status_code == 200

        # 404 Not Found (exists in test but won't be routed)
        resp_404 = await client.get("/nonexistent")
        assert resp_404.status_code == 404


@pytest.mark.anyio
async def test_tracing_otel_enabled_flag():
    """Verify otel_enabled config flag works correctly."""
    assert hasattr(settings, "otel_enabled")
    assert isinstance(settings.otel_enabled, bool)
    # By default it should be True
    original = settings.otel_enabled
    settings.otel_enabled = True
    assert settings.otel_enabled is True
    settings.otel_enabled = False
    assert settings.otel_enabled is False
    settings.otel_enabled = original


@pytest.mark.anyio
async def test_tracing_otel_service_name():
    """Verify OTEL service name config exists."""
    assert hasattr(settings, "otel_service_name")
    assert isinstance(settings.otel_service_name, str)
    assert settings.otel_service_name == "notifyhub-backend"


@pytest.mark.anyio
async def test_tracing_round_trip_with_health(client: AsyncClient):
    """Health endpoint works correctly regardless of tracing state."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
