from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from redis.asyncio import Redis

from app.core.config import settings
from app.services.rate_limit_service import RateLimitService

logger = logging.getLogger(__name__)


def _is_excluded(path: str) -> bool:
    excluded = set(settings.rate_limit_excluded_paths)
    if path in excluded:
        return True
    # Also exclude docs/openapi-like prefixes.
    if any(path.startswith(p) for p in settings.rate_limit_excluded_prefixes):
        return True
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        if _is_excluded(request.url.path):
            return await call_next(request)

        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Resolve endpoint-specific rule.
        endpoint_rule = settings.rate_limit_rules.get((request.method, request.url.path))
        if endpoint_rule is None:
            # Support prefix match as a simple way to add rules later.
            endpoint_rule = settings.rate_limit_rules.get((request.method, "*"))

        if endpoint_rule is None:
            return await call_next(request)

        client_ip = request.client.host if request.client else None

        user_id: str | None = None
        # If auth is available, routes/auth middleware typically sets request.state.user_id.
        # We fall back to Authorization header presence to distinguish anonymous vs authenticated.
        if hasattr(request.state, "user_id"):
            user_id = getattr(request.state, "user_id")
        else:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                # Authenticated user will be set by auth dependency in routes;
                # middleware runs before route dependency, so we keep user_id as None
                # and still rate-limit via IP unless request.state.user_id is set.
                user_id = None

        redis_client = settings._rate_limit_redis
        if redis_client is None:
            return await call_next(request)

        service = RateLimitService(redis=redis_client)

        # Authenticated vs anonymous limits: endpoint rule already includes the limit.
        decision = await service.check_and_update(
            user_id=user_id,
            ip=client_ip,
            endpoint_key=endpoint_rule["endpoint_key"],
            limit=int(endpoint_rule["limit"]),
            window_seconds=int(endpoint_rule["window_seconds"]),
        )


        headers = {
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
        }

        if decision.allowed:
            response = await call_next(request)
            # Ensure headers on successful responses too.
            for k, v in headers.items():
                response.headers[k] = v
            return response

        retry_after = decision.reset_after_seconds
        headers["Retry-After"] = str(retry_after)
        logger.info(
            "Request blocked by rate limiter",
            extra={"path": request.url.path, "method": request.method, "retry_after": retry_after},
        )
        return JSONResponse(
            status_code=429,
            content={"success": False, "message": "Rate limit exceeded."},
            headers=headers,
        )

