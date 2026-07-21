from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient) -> None:
    """GET /health should return 200 with service info."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "notifyhub"
    assert data["version"] == "1.0.0"


@pytest.mark.anyio
async def test_live_endpoint(client: AsyncClient) -> None:
    """GET /live should return 200 with alive status."""
    response = await client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.anyio
async def test_ready_endpoint_healthy(client: AsyncClient) -> None:
    """GET /ready should return 200 when dependencies are healthy."""
    from app.services.health_service import HealthService, DependencyCheckResult

    mock_check = AsyncMock(return_value=DependencyCheckResult(database=True, redis=True, celery="not_checked"))

    with patch.object(HealthService, "check_ready", mock_check):
        response = await client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


@pytest.mark.anyio
async def test_ready_endpoint_redis_unavailable(client: AsyncClient) -> None:
    """GET /ready should return 503 when Redis is unavailable."""
    from app.services.health_service import HealthService, DependencyCheckResult

    mock_check = AsyncMock(return_value=DependencyCheckResult(database=True, redis=False, celery="not_checked"))

    with patch.object(HealthService, "check_ready", mock_check):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["redis"] == "disconnected"


@pytest.mark.anyio
async def test_ready_endpoint_database_unavailable(client: AsyncClient) -> None:
    """GET /ready should return 503 when database is unavailable."""
    from app.services.health_service import HealthService, DependencyCheckResult

    mock_check = AsyncMock(return_value=DependencyCheckResult(database=False, redis=True, celery="not_checked"))

    with patch.object(HealthService, "check_ready", mock_check):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "disconnected"


@pytest.mark.anyio
async def test_ready_endpoint_all_unavailable(client: AsyncClient) -> None:
    """GET /ready should return 503 when all dependencies are unavailable."""
    from app.services.health_service import HealthService, DependencyCheckResult

    mock_check = AsyncMock(return_value=DependencyCheckResult(database=False, redis=False, celery="not_checked"))

    with patch.object(HealthService, "check_ready", mock_check):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "disconnected"
    assert data["redis"] == "disconnected"
