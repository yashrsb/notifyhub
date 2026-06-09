from __future__ import annotations

from typing import Any


def success_response(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error_response(message: str, *, data: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "message": message}
    if data is not None:
        payload["data"] = data
    return payload

