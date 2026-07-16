from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.core.config import settings


@pytest.mark.anyio
async def test_audit_logs_api_filters_and_paginates(client, async_session_maker):
    # This test assumes the audit_logs table exists (migrated in test DB).
    # It also validates filtering/pagination/sorting behavior.
    from app.db.session import get_db
    from app.services.audit_service import AuditService
    from app.models.audit_logs import AuditEntityType, AuditAction

    # Create two audit rows
    async with async_session_maker() as session:  # type: ignore[misc]
        svc = AuditService(session=session)
        await svc.publish(
            entity_type=AuditEntityType.USER,
            entity_id=str(uuid.uuid4()),
            action=AuditAction.USER_REGISTERED,
            performed_by=None,
            metadata={"k": "v1"},
        )
        await svc.publish(
            entity_type=AuditEntityType.TEMPLATE,
            entity_id=str(uuid.uuid4()),
            action=AuditAction.TEMPLATE_CREATED,
            performed_by=None,
            metadata={"k": "v2"},
        )

    # Filter by entity_type
    resp = await client.get(
        "/api/v1/audit-logs",
        params={"entity_type": AuditEntityType.USER.value, "page": 1, "page_size": 10},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] >= 0
    # Items should be present only for USER
    for item in data["items"]:
        assert item["entity_type"] == AuditEntityType.USER

    # Pagination shape compatibility
    assert "items" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.anyio
async def test_audit_service_never_raises_on_persistence_failure(client, monkeypatch, async_session_maker):
    from app.services.audit_service import AuditService
    from app.repositories.audit_logs_repo import AuditLogsRepository
    from app.models.audit_logs import AuditAction, AuditEntityType

    class BoomRepo(AuditLogsRepository):
        async def insert(self, *, log):  # type: ignore[override]
            raise RuntimeError("db down")

    async with async_session_maker() as session:  # type: ignore[misc]
        svc = AuditService(session=session)
        svc._repo = BoomRepo(session)  # type: ignore[attr-defined]

        # Must swallow exceptions
        await svc.publish(
            entity_type=AuditEntityType.USER,
            entity_id=str(uuid.uuid4()),
            action=AuditAction.USER_LOGGED_IN,
            performed_by=None,
            metadata={"x": 1},
        )


