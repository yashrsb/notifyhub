from __future__ import annotations

import pytest
import uuid


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_template_crud(client):
    # register/login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "t1@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "t1@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = _bearer(token)

    create = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "welcome",
            "subject": "Welcome {{name}}",
            "body": "Hello {{name}}",
        },
    )
    assert create.status_code == 200
    tpl = create.json()["data"]
    tpl_id = uuid.UUID(tpl["id"])

    # list
    listed = await client.get("/api/v1/templates", headers=headers)
    assert listed.status_code == 200
    assert any(x["id"] == str(tpl_id) for x in listed.json()["data"])

    # get
    got = await client.get(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == str(tpl_id)

    # update
    upd = await client.put(
        f"/api/v1/templates/{tpl_id}",
        headers=headers,
        json={
            "name": "welcome2",
            "subject": "Welcome {{name}}",
            "body": "Hello again {{name}}",
        },
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["name"] == "welcome2"

    # delete
    dele = await client.delete(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert dele.status_code == 200

