from __future__ import annotations

import time
import uuid

from fastapi import Request
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
from opentelemetry.trace import Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.tracing import get_tracer

tracer = get_tracer("notifyhub.http")


class TracingHTTPMiddleware(BaseHTTPMiddleware):
    """Middleware that creates a root span for every incoming HTTP request.

    Span name: {METHOD} {route}
    Attributes: http.method, http.route, http.status_code, http.duration_ms, request.id

    Trace context is injected into response headers for downstream propagation.
    If the incoming request already carries trace headers (from a gateway/proxy),
    they are extracted and used as the parent context.

    Business-level attributes (notification.*, provider.*, etc.) are added
    by downstream service instrumentation, not here.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        if not tracer:
            return await call_next(request)

        # Extract any incoming trace context
        ctx = extract(request.headers)

        span_name = f"{request.method} {request.url.path}"

        with tracer.start_as_current_span(span_name, context=ctx, kind=trace.SpanKind.SERVER) as span:
            # Core HTTP attributes only — no duplicate or noisy attributes.
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", request.url.path)

            # Set request ID if present
            request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
            span.set_attribute("request.id", request_id)

            # Attach to request state for downstream use
            request.state.trace_context = ctx
            request.state.span = span

            start = time.monotonic()

            try:
                response: Response = await call_next(request)

                # Inject trace context into response headers
                carrier: dict[str, str] = {}
                inject(carrier)
                for k, v in carrier.items():
                    response.headers[k] = v

                span.set_attribute("http.status_code", response.status_code)

                duration = time.monotonic() - start
                span.set_attribute("http.duration_ms", duration * 1000)

                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.UNSET))

                return response

            except Exception as e:
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
