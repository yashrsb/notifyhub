from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_register_and_login(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "john@example.com", "password": "Password123!"},
    )
    assert reg.status_code == 200
    body = reg.json()
    assert body["success"] is True
    assert body["data"]["email"] == "john@example.com"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "john@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token


@pytest.mark.anyio
async def test_login_invalid_credentials(client):
    # wrong password
    await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "Password123!"},
    )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "WrongPass"},
    )
    assert login.status_code == 401 or login.status_code == 400

