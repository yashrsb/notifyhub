from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def _rate_limit_test_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure limiter is enabled.
    monkeypatch.setattr(settings, "rate_limit_enabled", True, raising=False)
    monkeypatch.setattr(settings, "rate_limit_algorithm", "token_bucket", raising=False)


@pytest.mark.anyio
async def test_rate_limit_429_response(client: AsyncClient):
    # Configure POST /notifications to a low limit for deterministic test.
    # We rely on the middleware's static mapping for the endpoint.
    settings.rate_limit_rules[("POST", "/notifications")]["limit"] = 2
    settings.rate_limit_rules[("POST", "/notifications")]["window_seconds"] = 3600

    # Auth headers
    await client.post(
        "/api/v1/auth/register",
        json={"email": "rl1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rl1@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Need template id
    create_tpl = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "t", "subject": "s", "body": "b"},
    )
    tpl_id = create_tpl.json()["data"]["id"]

    # Send 3 requests; limit=2 so 3rd should be 429.
    payload = {
        "channel": "EMAIL",
        "recipient": "a@example.com",
        "template_id": tpl_id,
        "variables": {},
    }

    # Idempotency-key required by notifications POST
    for i in range(2):
        res = await client.post(
            "/api/v1/notifications",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json=payload,
        )
        assert res.status_code == 202

    res3 = await client.post(
        "/api/v1/notifications",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json=payload,
    )
    assert res3.status_code == 429
    body = res3.json()
    assert body["success"] is False
    assert body["message"] == "Rate limit exceeded."
    assert "Retry-After" in res3.headers


@pytest.mark.anyio
async def test_excluded_health_not_limited(client: AsyncClient):
    # Even if we crank down limits, /health should not be excluded.
    settings.rate_limit_enabled = True
    settings.rate_limit_excluded_paths = ["/health"]

    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.anyio
async def test_concurrent_requests_respect_limit(client: AsyncClient):
    settings.rate_limit_rules[("POST", "/notifications")]["limit"] = 5
    settings.rate_limit_rules[("POST", "/notifications")]["window_seconds"] = 3600

    await client.post(
        "/api/v1/auth/register",
        json={"email": "rl2@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rl2@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_tpl = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "t2", "subject": "s", "body": "b"},
    )
    tpl_id = create_tpl.json()["data"]["id"]

    payload = {
        "channel": "EMAIL",
        "recipient": "b@example.com",
        "template_id": tpl_id,
        "variables": {},
    }

    async def do_one(n: int):
        return await client.post(
            "/api/v1/notifications",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json=payload,
        )

    results = await asyncio.gather(*[do_one(i) for i in range(12)])
    # At least some should be 429.
    codes = [r.status_code for r in results]
    assert 429 in codes
    assert 202 in codes
