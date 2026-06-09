from __future__ import annotations

import pytest
import uuid


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_create_notification_renders_template(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "n1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "n1@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = _bearer(token)

    create_tpl = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "hello",
            "subject": "Welcome {{name}}",
            "body": "Hello {{name}}, bye",
        },
    )
    tpl_id = uuid.UUID(create_tpl.json()["data"]["id"])

    notif = await client.post(
        "/api/v1/notifications",
        headers=headers,
        json={
            "channel": "email",
            "recipient": "john@example.com",
            "template_id": str(tpl_id),
            "variables": {"name": "John"},
        },
    )
    assert notif.status_code == 200
    data = notif.json()["data"]
    assert data["rendered_subject"] == "Welcome John"
    assert data["rendered_body"] == "Hello John, bye"

    # list
    listed = await client.get("/api/v1/notifications", headers=headers)
    assert listed.status_code == 200
    assert any(x["id"] == data["id"] for x in listed.json()["data"])

    # get
    got = await client.get(f"/api/v1/notifications/{data['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == data["id"]

