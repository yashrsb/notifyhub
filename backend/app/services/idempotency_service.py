from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from opentelemetry import trace
from redis import Redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.idempotency_keys import IdempotencyKey
from app.repositories.idempotency_keys_repo import IdempotencyKeysRepository
from app.services.notification_service import create_notification
from app.tasks.notifications_tasks import process_notification_task

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("notifyhub.idempotency")


@dataclass(frozen=True)
class IdempotencyResult:
    response_body: dict[str, Any]
    status_code: int
    notification_id: uuid.UUID


class IdempotencyService:
    def __init__(self, *, redis_client: Redis):
        self._redis = redis_client

    def _request_hash(self, *, recipient: str, channel: str, template_id: uuid.UUID, variables: dict[str, Any]) -> str:
        payload = {
            "recipient": recipient,
            "channel": channel,
            "template_id": str(template_id),
            "variables": variables,
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _redis_cache_key(self, *, key: str) -> str:
        return f"idempotency:{key}"

    def _redis_lock_key(self, *, key: str) -> str:
        return f"lock:idempotency:{key}"

    async def process_create(
        self,
        *,
        idempotency_key: str,
        session: AsyncSession,
        channel: str,
        recipient: str,
        template_id: uuid.UUID,
        variables: dict[str, Any],
    ) -> IdempotencyResult:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="Missing Idempotency-Key header")

        # 1) Redis cache fast path
        cache_key = self._redis_cache_key(key=idempotency_key)
        if settings.otel_enabled:
            with tracer.start_as_current_span("Redis.Idempotency") as span:
                span.set_attribute("idempotency.key", idempotency_key)
                span.set_attribute("redis.operation", "cache_get")
                cached = self._redis.get(cache_key)
        else:
            cached = self._redis.get(cache_key)
        if cached is not None:
            logger.info("Idempotency cache hit", extra={"idempotency_key": idempotency_key})
            body = json.loads(cached)
            return IdempotencyResult(
                response_body=body["response_body"],
                status_code=int(body["status_code"]),
                notification_id=uuid.UUID(body["notification_id"]),
            )

        # 2) Distributed lock
        lock_key = self._redis_lock_key(key=idempotency_key)
        lock_token = str(time.time_ns())
        if settings.otel_enabled:
            with tracer.start_as_current_span("Redis.Idempotency") as span:
                span.set_attribute("idempotency.key", idempotency_key)
                span.set_attribute("redis.operation", "lock_acquire")
                lock_acquired = self._redis.set(lock_key, lock_token, nx=True, ex=30)
        else:
            lock_acquired = self._redis.set(lock_key, lock_token, nx=True, ex=30)

        if not lock_acquired:
            # Another request is creating/processing the same key.
            raise HTTPException(status_code=409, detail="Duplicate request in progress")

        try:
            # 3) Validate request hash vs DB
            request_hash = self._request_hash(
                recipient=recipient,
                channel=channel,
                template_id=template_id,
                variables=variables,
            )

            repo = IdempotencyKeysRepository(session)
            existing = await repo.get_by_key(key=idempotency_key)

            if existing is not None:
                if existing.request_hash != request_hash:
                    logger.info(
                        "Hash mismatch",
                        extra={"idempotency_key": idempotency_key, "notification_id": str(existing.notification_id)},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key reused with different request.",
                    )

                logger.info(
                    "Database hit (idempotent)",
                    extra={"idempotency_key": idempotency_key, "notification_id": str(existing.notification_id)},
                )
                return IdempotencyResult(
                    response_body=existing.response_body,
                    status_code=existing.status_code,
                    notification_id=existing.notification_id,
                )

            # 4) Create notification only once
            logger.info(
                "Creating new notification (idempotent)",
                extra={"idempotency_key": idempotency_key},
            )
            notif = await create_notification(
                session=session,
                channel=channel,
                recipient=recipient,
                template_id=template_id,
                variables=variables,
            )

            logger.info("Queueing notification task", extra={"notification_id": str(notif.id)})
            process_notification_task.delay(str(notif.id))

            # 5) Persist idempotency record
            ttl = timedelta(hours=24)
            expires_at = datetime.now(timezone.utc) + ttl

            response_body = {
                "success": True,
                "message": "Notification queued",
                "notification_id": notif.id,
            }

            await repo.create(
                key=idempotency_key,
                request_hash=request_hash,
                notification_id=notif.id,
                response_body={
                    "success": True,
                    "message": "Notification queued",
                    "notification_id": notif.id,
                },
                status_code=status.HTTP_202_ACCEPTED,
                expires_at=expires_at,
            )

            # 6) Store response in Redis cache
            cache_payload = {
                "status_code": status.HTTP_202_ACCEPTED,
                "notification_id": str(notif.id),
                "response_body": response_body,
            }
            if settings.otel_enabled:
                with tracer.start_as_current_span("Redis.Idempotency") as span:
                    span.set_attribute("idempotency.key", idempotency_key)
                    span.set_attribute("redis.operation", "cache_set")
                    self._redis.set(cache_key, json.dumps(cache_payload, default=str), ex=int(ttl.total_seconds()))
            else:
                self._redis.set(cache_key, json.dumps(cache_payload, default=str), ex=int(ttl.total_seconds()))

            return IdempotencyResult(
                response_body=response_body,
                status_code=status.HTTP_202_ACCEPTED,
                notification_id=notif.id,
            )

        finally:
            # Release lock
            # Best effort release: only delete if our token matches.
            if settings.otel_enabled:
                with tracer.start_as_current_span("Redis.Idempotency") as span:
                    span.set_attribute("idempotency.key", idempotency_key)
                    span.set_attribute("redis.operation", "lock_release")
                    current = self._redis.get(lock_key)
                    if current is not None and current.decode("utf-8") == lock_token:
                        self._redis.delete(lock_key)
            else:
                current = self._redis.get(lock_key)
                if current is not None and current.decode("utf-8") == lock_token:
                    self._redis.delete(lock_key)
            logger.info("Lock released", extra={"idempotency_key": idempotency_key})
