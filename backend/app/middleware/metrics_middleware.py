from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics_service import metrics


class MetricsHTTPMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records HTTP-level Prometheus metrics.

    Captures request count, latency, and response status for every request
    that passes through the pipeline.  Runs after rate-limiting but before
    route handling.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Record start time
        start = time.monotonic()

        try:
            response: Response = await call_next(request)
            return response
        finally:
            # Compute duration regardless of exceptions
            duration = time.monotonic() - start
            method = request.method
            endpoint = request.url.path
            status_code = getattr(response, "status_code", 500) if "response" in dir() else 500

            metrics.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
            )


__all__ = ["MetricsHTTPMiddleware"]
