from __future__ import annotations

import uuid

import pytest


@pytest.mark.anyio
async def test_template_audit_created_updated_deleted(client, monkeypatch):
    # Capture audit logs persisted by spying on AuditService.publish.
    from app.services.audit_service import AuditService
    from app.models.audit_logs import AuditAction

    publish_spy_calls: list[dict] = []

    async def fake_publish(self: AuditService, *, entity_type, entity_id, action, performed_by, metadata=None):  # type: ignore[override]
        publish_spy_calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "performed_by": performed_by,
                "metadata": metadata,
            }
        )
        return None

    monkeypatch.setattr(AuditService, "publish", fake_publish)

    # register/login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "tpl-audit@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "tpl-audit@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "n1", "subject": "s1", "body": "b1"},
    )
    assert create.status_code == 200
    tpl_id = uuid.UUID(create.json()["data"]["id"])

    # update
    upd = await client.put(
        f"/api/v1/templates/{tpl_id}",
        headers=headers,
        json={"name": "n2", "subject": "s2", "body": "b2"},
    )
    assert upd.status_code == 200

    # delete
    dele = await client.delete(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert dele.status_code == 200

    # We expect TEMPLATE_CREATED, TEMPLATE_UPDATED, TEMPLATE_DELETED.
    actions = [c["action"] for c in publish_spy_calls if c["action"] in set(AuditAction)]
    assert AuditAction.TEMPLATE_CREATED in actions
    assert AuditAction.TEMPLATE_UPDATED in actions
    assert AuditAction.TEMPLATE_DELETED in actions


    assert created_call["metadata"]["created_by"] is not None
    assert created_call["performed_by"] is not None

    updated_call = next(c for c in publish_spy_calls if c["action"] == AuditAction.TEMPLATE_UPDATED)
    assert updated_call["metadata"]["template_id"] == str(tpl_id)
    assert "updated_fields" in updated_call["metadata"]

    deleted_call = next(c for c in publish_spy_calls if c["action"] == AuditAction.TEMPLATE_DELETED)
    assert deleted_call["metadata"]["template_id"] == str(tpl_id)
    assert deleted_call["metadata"]["channel"] == "email"


@pytest.mark.anyio
async def test_template_audit_failure_does_not_break(client, monkeypatch):
    # Force AuditService.publish to throw.
    from app.services.audit_service import AuditService

    async def boom_publish(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("audit down")

    monkeypatch.setattr(AuditService, "publish", boom_publish)

    await client.post(
        "/api/v1/auth/register",
        json={"email": "tpl-audit-fail@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "tpl-audit-fail@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "n1", "subject": "s1", "body": "b1"},
    )
    assert create.status_code == 200

    tpl_id = uuid.UUID(create.json()["data"]["id"])

    upd = await client.put(
        f"/api/v1/templates/{tpl_id}",
        headers=headers,
        json={"name": "n2", "subject": "s2", "body": "b2"},
    )
    assert upd.status_code == 200

    dele = await client.delete(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert dele.status_code == 200

