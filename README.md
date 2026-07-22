# notifyhub (Phase 2)

## Architecture

Client
↓
FastAPI
↓
PostgreSQL
↓
Redis Queue
↓
Celery Worker
↓
Notification Processor (EmailProvider)

## Endpoints

- `POST /api/v1/notifications`
  - Creates notification record
  - Enqueues Celery job
  - Returns **HTTP 202**:

```json
{
  "success": true,
  "message": "Notification queued",
  "notification_id": "<uuid>"
}
```

- `GET /api/v1/notifications/{id}`
  - Returns status and persisted attempts

## Retry schedule
- Attempt #1: immediately
- Attempt #2: after 30 seconds
- Attempt #3: after 60 seconds

If all retries fail:
- Notification status becomes `FAILED`
- The final error is stored in `notification_attempts`.

## Starting services (Docker)

From repo root:

```bash
docker-compose -f backend/docker-compose.yml up --build
```

Run migrations:

```bash
docker-compose -f backend/docker-compose.yml exec backend alembic upgrade head
```

## Worker

The Celery worker is started via docker-compose.

Logs will include:
- Notification Queued
- Notification Processing Started
- Retry Attempt
- Notification Sent
- Notification Failed

## Distributed Tracing (Phase 7C)

### Overview

Distributed tracing is implemented using OpenTelemetry. A single trace follows a notification request across all components:

**Trace flow:**
```
HTTP Request → FastAPI → Auth → Rate Limiting
→ Idempotency → Notification Service → PostgreSQL
→ Redis → Celery → Worker → ProviderFactory → Provider
```

### Component vs Instrumentation

| Component | Instrumentation | Type |
|-----------|----------------|------|
| HTTP requests | `TracingHTTPMiddleware` | Manual |
| SQL queries | `SQLAlchemyInstrumentor` | Automatic |
| Redis operations | `RedisInstrumentor` | Automatic |
| Celery produce/consume | `CeleryInstrumentor` | Automatic |
| asyncpg queries | `asyncpg instrumentor` | Automatic |
| Provider resolution | `Provider.Resolve` span | Manual |
| Worker processing | `Notification.Process` span | Manual |
| Retry attempt | `Notification.Retry` span | Manual |
| Dead-letter | `Worker.DeadLetter` span | Manual |
| Idempotency cache/lock | `Redis.Idempotency` span | Manual |

### Span naming convention

All manually created spans follow business-oriented names using dot-separated notation:

| Span name | Location | Description |
|-----------|----------|-------------|
| `Notification.Process` | `notification_worker_service.py` | Full notification processing lifecycle |
| `Notification.Retry` | `notifications_tasks.py` | Scheduled retry after failure |
| `Notification.Queue` | (implicit via automatic Celery) | Task enqueued |
| `Provider.Resolve` | `factory.py` | Provider resolution from channel |
| `Redis.Idempotency` | `idempotency_service.py` | Redis cache/lock operations |
| `Worker.DeadLetter` | `notifications_tasks.py` | Final failure after retries exhausted |

Generic names like `process`, `task`, `send`, `redis`, `provider` are **avoided**. Every span name immediately describes the business operation.

### Span attributes

All attributes follow a consistent namespace convention:

**HTTP** (`http.*`):
- `http.method` — e.g. `POST`, `GET`
- `http.route` — URL path, e.g. `/api/v1/notifications`
- `http.status_code` — HTTP response status
- `http.duration_ms` — Request processing time
- `request.id` — Unique request identifier

**Notification** (`notification.*`):
- `notification.id` — UUID of the notification
- `notification.template_id` — UUID of the associated template
- `notification.channel` — e.g. `EMAIL`, `SMS`, `PUSH`
- `notification.status` — `PENDING`, `PROCESSING`, `SENT`, `FAILED`
- `notification.duration_ms` — Processing duration
- `notification.dead_letter` — `true` when all retries exhausted

**Provider** (`provider.*`):
- `provider.name` — e.g. `EmailProviderAdapter`, `SMSProvider`
- `provider.channel` — e.g. `EMAIL`, `SMS`, `PUSH`

**Retry** (`retry.*`):
- `retry.count` — Attempt number (1, 2, or 3)

**Redis** (`redis.*`):
- `redis.operation` — e.g. `cache_get`, `lock_acquire`, `cache_set`, `lock_release`

**Idempotency** (`idempotency.*`):
- `idempotency.key` — The idempotency key being processed

**Error** (`error.*`):
- `error.message` — Exception message

### Resource attributes

Every trace is tagged with these resource attributes:

| Attribute | Source | Example |
|-----------|--------|---------|
| `service.name` | `settings.otel_service_name` | `notifyhub-backend` |
| `service.version` | `settings.service_version` | `1.0.0` |
| `deployment.environment` | `settings.deployment_environment` | `development` |
| `host.name` | System hostname | `my-machine` |
| `service.instance.id` | `SERVICE_INSTANCE_ID` env or hostname | `my-machine` |

All resource attributes come from configuration or system values — **nothing is hardcoded**.

### Trace context propagation

The trace context flows from FastAPI to Celery via:
1. `TracingHTTPMiddleware` injects trace headers into HTTP responses
2. Celery instrumentation propagates trace context automatically from producer to worker
3. The worker continues the same trace (does not create a new root trace)

### Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `true` | Set to `false` to disable tracing globally |
| `OTEL_SERVICE_NAME` | `notifyhub-backend` | Service name reported in traces |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `""` | OTLP HTTP endpoint (e.g. `http://collector:4318/v1/traces`). Empty = console only |
| `SERVICE_VERSION` | `1.0.0` | Version reported in `service.version` resource attribute |
| `DEPLOYMENT_ENVIRONMENT` | `development` | Environment reported in `deployment.environment` resource attribute |

### Disabling tracing

Set `OTEL_ENABLED=false` to disable all tracing. When disabled:
- The tracer provider is not created
- All manual instrumentation checks `settings.otel_enabled` before creating spans
- Middleware returns `await call_next(request)` immediately without tracing

### Exporters

- **ConsoleSpanExporter**: Always enabled when `OTEL_ENABLED=true`. Spans are printed to stdout.
- **OTLPSpanExporter**: Enabled when `OTEL_EXPORTER_OTLP_ENDPOINT` is non-empty. Supports any OTLP-compatible backend.

### Business-level instrumentation philosophy

Instrumentation exists **only at business boundaries**:

- **Instrumented**: HTTP entry, provider resolution, notification processing, retry attempt, dead-letter handling, idempotency operations
- **Not instrumented**: helper functions, validation, serialization, template rendering, configuration loading, utility methods

This ensures:
- The trace clearly shows the business flow without becoming noisy
- Spans are meaningful and immediately understandable
- Performance overhead is minimized by avoiding unnecessary spans

### PII exclusion

**No personally identifiable information (PII) is stored in span attributes.**

Explicitly excluded from traces:
- Recipient email addresses
- Phone numbers
- Message bodies (rendered subject/body)
- JWT tokens
- Authorization headers
- Passwords

Only operational identifiers and metadata are included:
- Notification UUIDs
- Template UUIDs (not template content)
- Channel names
- Status values
- Attempt counts

### Adding new instrumentation

To add tracing to a new component:

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from app.core.config import settings

tracer = trace.get_tracer("notifyhub.my_component")

if settings.otel_enabled:
    with tracer.start_as_current_span("Component.Operation") as span:
        span.set_attribute("namespace.attribute", value)
        # ... business logic
        span.set_status(Status(StatusCode.OK))
```

**Best practices:**
1. Use business-oriented span names with dot notation (e.g. `Notification.Process`, `Provider.Resolve`)
2. Keep attributes namespaced consistently (e.g. `notification.*`, `provider.*`, `redis.*`)
3. Record exceptions via `span.record_exception(e)` and set `span.set_status(Status(StatusCode.ERROR, str(e)))`
4. Never store PII in attributes
5. Always guard with `if settings.otel_enabled:` to support disabling
6. Prefer fewer, high-quality spans over many low-value spans
