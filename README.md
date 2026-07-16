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

