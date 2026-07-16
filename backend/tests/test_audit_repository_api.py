from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.models.audit_logs import AuditAction, AuditEntityType
from app.services.audit_service import AuditService


@pytest.mark.anyio
async def test_audit_logs_api_sorting_and_metadata_shape(client, async_session_maker):
    async with async_session_maker() as session:  # type: ignore[misc]
        svc = AuditService(session=session)
        await svc.publish(
            entity_type=AuditEntityType.USER,
            entity_id=str(uuid.uuid4()),
            action=AuditAction.USER_REGISTERED,
            performed_by=None,
            metadata={"foo": "bar"},
        )

    resp = await client.get(
        "/api/v1/audit-logs",
        params={
            "entity_type": AuditEntityType.USER.value,
            "sort": "created_at",
            "sort_dir": "desc",
            "page": 1,
            "page_size": 10,
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert set(data.keys()) >= {"items", "total", "page", "page_size"}
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        assert "metadata" in item
        assert isinstance(item["metadata"], dict)

