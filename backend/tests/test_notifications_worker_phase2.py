from __future__ import annotations

import uuid

import pytest


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_worker_success_path(client, monkeypatch):
    # Force provider to succeed.
    from app.providers import email_provider

    monkeypatch.setattr(email_provider.random, "random", lambda: 0.99)  # type: ignore[attr-defined]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "s1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "s1@example.com", "password": "Password123!"},
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
    assert notif.status_code == 202
    notification_id = uuid.UUID(notif.json()["notification_id"])

    # With eager mode in tests, Celery task runs immediately.
    got = await client.get(f"/api/v1/notifications/{notification_id}", headers=headers)
    assert got.status_code == 200
    data = got.json()["data"]
    assert data["status"] == "SENT"
    assert len(data["attempts"]) == 1
    assert data["attempts"][0]["attempt"] == 1
    assert data["attempts"][0]["status"] == "SUCCESS"


@pytest.mark.anyio
async def test_worker_retry_then_success(client, monkeypatch):
    # Fail first 2 attempts, succeed on 3rd.
    call_count = {"n": 0}

    from app.providers import email_provider

    def fake_random() -> float:
        call_count["n"] += 1
        return 0.0 if call_count["n"] < 3 else 0.99

    monkeypatch.setattr(email_provider.random, "random", fake_random)  # type: ignore[attr-defined]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "r1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "r1@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = _bearer(token)

    create_tpl = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "hello2",
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
            "recipient": "retry@example.com",
            "template_id": str(tpl_id),
            "variables": {"name": "Retry"},
        },
    )
    assert notif.status_code == 202
    notification_id = uuid.UUID(notif.json()["notification_id"])

    got = await client.get(f"/api/v1/notifications/{notification_id}", headers=headers)
    assert got.status_code == 200
    data = got.json()["data"]

    assert data["status"] == "SENT"
    assert [a["attempt"] for a in data["attempts"]] == [1, 2, 3]
    assert [a["status"] for a in data["attempts"]] == ["FAILED", "FAILED", "SUCCESS"]


@pytest.mark.anyio
async def test_worker_final_failure(client, monkeypatch):
    # Always fail.
    from app.providers import email_provider

    monkeypatch.setattr(email_provider.random, "random", lambda: 0.0)  # type: ignore[attr-defined]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "f1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "f1@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = _bearer(token)

    create_tpl = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "hello3",
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
            "recipient": "fail@example.com",
            "template_id": str(tpl_id),
            "variables": {"name": "Fail"},
        },
    )
    assert notif.status_code == 202
    notification_id = uuid.UUID(notif.json()["notification_id"])

    got = await client.get(f"/api/v1/notifications/{notification_id}", headers=headers)
    assert got.status_code == 200
    data = got.json()["data"]

    assert data["status"] == "FAILED"
    assert [a["attempt"] for a in data["attempts"]] == [1, 2, 3]
    assert all(a["status"] == "FAILED" for a in data["attempts"])
    assert data["attempts"][-1]["error"] is not None

