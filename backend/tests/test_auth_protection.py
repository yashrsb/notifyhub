from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_templates_requires_auth(client):
    res = await client.get("/api/v1/templates")
    # OAuth2PasswordBearer returns 401 without token
    assert res.status_code in (401, 403)

