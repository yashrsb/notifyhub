from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


RateLimitAlgorithm = Literal["token_bucket", "sliding_window"]


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int


class RateLimitService:
    """Redis-backed rate limiting service.

    Implements Token Bucket (primary) and Sliding Window (placeholder skeleton).
    Business logic lives here; middleware only calls this service.
    """

    def __init__(self, *, redis: Redis) -> None:
        self._redis = redis
        self._algorithm: RateLimitAlgorithm = settings.rate_limit_algorithm

    def _make_key(self, *, user_id: str | None, ip: str | None, endpoint_key: str) -> str:
        if user_id:
            return f"rate_limit:user:{user_id}:{endpoint_key}"
        if ip:
            return f"rate_limit:ip:{ip}:{endpoint_key}"
        # Should not happen; fallback to a stable anon bucket.
        return f"rate_limit:ip:unknown:{endpoint_key}"

    def _retry_after_seconds(self, *, reset_after_seconds: int) -> int:
        return max(0, int(reset_after_seconds))

    async def check_and_update(
        self,
        *,
        user_id: str | None,
        ip: str | None,
        endpoint_key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        if limit <= 0:
            # Disable for this rule.
            return RateLimitDecision(allowed=True, limit=limit, remaining=0, reset_after_seconds=0)

        # Capacity = limit; refill rate = limit per window.
        if self._algorithm == "token_bucket":
            return await self._token_bucket(
                user_id=user_id,
                ip=ip,
                endpoint_key=endpoint_key,
                capacity=limit,
                refill_rate_per_second=limit / window_seconds,
                window_seconds=window_seconds,
            )

        # Skeleton for future extension.
        if self._algorithm == "sliding_window":
            return await self._sliding_window_placeholder(
                user_id=user_id,
                ip=ip,
                endpoint_key=endpoint_key,
                limit=limit,
                window_seconds=window_seconds,
            )

        # Unknown algorithm fallback.
        return await self._token_bucket(
            user_id=user_id,
            ip=ip,
            endpoint_key=endpoint_key,
            capacity=limit,
            refill_rate_per_second=limit / window_seconds,
            window_seconds=window_seconds,
        )

    async def _token_bucket(
        self,
        *,
        user_id: str | None,
        ip: str | None,
        endpoint_key: str,
        capacity: int,
        refill_rate_per_second: float,
        window_seconds: int,
    ) -> RateLimitDecision:
        key = self._make_key(user_id=user_id, ip=ip, endpoint_key=endpoint_key)
        now = int(time.time())
        # Store state as: tokens (float) + last_refill_ts (int)
        # Use Lua for atomic update.
        lua = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local data = redis.call('HMGET', key, 'tokens', 'ts')
        local tokens = tonumber(data[1])
        local ts = tonumber(data[2])

        if tokens == nil then
            tokens = capacity
            ts = now
        end

        local delta = now - ts
        if delta < 0 then delta = 0 end
        local new_tokens = tokens + (delta * refill)
        if new_tokens > capacity then new_tokens = capacity end

        local allowed = 0
        local remaining = 0
        local retry_after = 0

        if new_tokens >= 1 then
            new_tokens = new_tokens - 1
            allowed = 1
            remaining = math.floor(new_tokens)
        else
            allowed = 0
            remaining = 0
            -- tokens to wait for 1 token
            local missing = 1 - new_tokens
            if refill > 0 then
                retry_after = math.ceil(missing / refill)
            else
                retry_after = 60
            end
        end

        redis.call('HSET', key, 'tokens', new_tokens, 'ts', now)
        -- TTL: keep slightly longer than window
        redis.call('EXPIRE', key, tonumber(ARGV[4]))

        return {allowed, capacity, remaining, retry_after}
        """
        retry_ttl = window_seconds * 2
        allowed, limit_ret, remaining, retry_after = await self._redis.eval(
            lua,
            1,
            key,
            str(capacity),
            str(refill_rate_per_second),
            str(now),
            str(retry_ttl),
        )

        allowed_bool = int(allowed) == 1
        # If blocked, reset_after_seconds is retry_after; if allowed, it's 0.
        reset_after_seconds = int(retry_after) if not allowed_bool else 0

        return RateLimitDecision(
            allowed=allowed_bool,
            limit=int(limit_ret),
            remaining=int(remaining),
            reset_after_seconds=reset_after_seconds,
        )

    async def _sliding_window_placeholder(
        self,
        *,
        user_id: str | None,
        ip: str | None,
        endpoint_key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        # Placeholder skeleton: always allow.
        # Sliding window can be implemented later without changing middleware.
        return RateLimitDecision(allowed=True, limit=limit, remaining=limit, reset_after_seconds=0)

