from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from app.core.exceptions import AuthError
from app.models.audit_logs import AuditAction, AuditEntityType
from app.services.audit_service import AuditService


@pytest.mark.anyio
async def test_user_registered_creates_audit_record(client, monkeypatch):
    # Patch AuditService.publish to track calls but still succeed.
    from app import services

    publish_spy = AsyncMock()

    async def fake_publish(*args, **kwargs):
        publish_spy(*args, **kwargs)
        return None

    monkeypatch.setattr(AuditService, "publish", fake_publish)

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "auditreg@example.com", "password": "Password123!"},
    )
    assert reg.status_code == 200
    body = reg.json()
    user_id = uuid.UUID(body["data"]["id"])

    assert publish_spy.called
    call = publish_spy.call_args
    kwargs = call.kwargs
    assert kwargs["entity_type"] == AuditEntityType.USER
    assert kwargs["entity_id"] == str(user_id)
    assert kwargs["performed_by"] == user_id


    assert kwargs["action"] == AuditAction.USER_REGISTERED

    metadata = kwargs.get("metadata")
    assert metadata is not None
    assert metadata["email"] == "auditreg@example.com"
    assert metadata["username"] is not None


@pytest.mark.anyio
async def test_user_logged_in_creates_audit_record(client, monkeypatch):
    publish_spy = AsyncMock()

    async def fake_publish(*args, **kwargs):
        publish_spy(*args, **kwargs)
        return None

    monkeypatch.setattr(AuditService, "publish", fake_publish)

    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"email": "auditlogin@example.com", "password": "Password123!"},
    )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "auditlogin@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200

    assert publish_spy.called

    # Last call should be USER_LOGGED_IN
    last_call = publish_spy.call_args_list[-1]
    kwargs = last_call.kwargs
    assert kwargs["entity_type"] == AuditEntityType.USER
    assert kwargs["action"] == AuditAction.USER_LOGGED_IN
    assert kwargs["performed_by"] == kwargs["entity_id"]
    assert kwargs["metadata"]["email"] == "auditlogin@example.com"


@pytest.mark.anyio
async def test_auth_succeeds_even_if_audit_service_throws(client, monkeypatch):
    async def boom_publish(*args, **kwargs):
        raise RuntimeError("audit db down")

    monkeypatch.setattr(AuditService, "publish", boom_publish)

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "auditthrows@example.com", "password": "Password123!"},
    )
    assert reg.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "auditthrows@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200

