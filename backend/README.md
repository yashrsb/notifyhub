# notifyhub (Phase 1)

Multi-Channel Notification Platform foundation (FastAPI + Async SQLAlchemy + JWT).

## Requirements
- Docker + Docker Compose

## Setup
### 1) Start services
From repo root:
```bash
docker-compose -f backend/docker-compose.yml up --build
```

### 2) Run migrations
In a second terminal:
```bash
docker-compose -f backend/docker-compose.yml exec backend alembic upgrade head
```

### 3) Open API docs
- http://localhost:8000/docs
- http://localhost:8000/openapi.json

## Environment variables
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`

See `.env.example`.

## API overview
Base path: `/api/v1`

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Templates (authenticated)
- `POST /templates`
- `GET /templates`
- `GET /templates/{id}`
- `PUT /templates/{id}`
- `DELETE /templates/{id}`

### Notifications (authenticated)
- `POST /notifications`
- `GET /notifications`
- `GET /notifications/{id}`

## Architecture overview
- `app/api`: routers
- `app/core`: config, security, exception handling, response envelope
- `app/db`: async engine/session
- `app/models`: SQLAlchemy models
- `app/schemas`: Pydantic v2 schemas
- `app/repositories`: DB persistence layer
- `app/services`: business logic (rendering templates)
- `app/dependencies`: FastAPI dependencies (auth)

