from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 60

    # Celery / Redis
    redis_broker_url: str
    redis_result_backend_url: str
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True

    # Email simulation
    email_simulation_enabled: bool = True
    email_failure_rate: float = 0.3

    # Idempotency
    idempotency_cache_ttl_seconds: int = 24 * 60 * 60
    idempotency_lock_ttl_seconds: int = 30

    # Health checks
    healthcheck_enabled: bool = True
    readiness_check_database: bool = True
    readiness_check_redis: bool = True
    readiness_check_celery: bool = False

    # Metrics
    metrics_enabled: bool = True
    prometheus_enabled: bool = True


# Rate limiting configuration
# NOTE: redis client is created lazily here but stored for middleware reuse.
settings = Settings()

# Build runtime rate-limit config derived from env.
# Middleware references these attributes dynamically.
settings.rate_limit_enabled = getattr(settings, "rate_limit_enabled", True)
settings.rate_limit_algorithm = getattr(settings, "RATE_LIMIT_ALGORITHM", "token_bucket")

# Endpoint exclusions
settings.rate_limit_excluded_paths = getattr(settings, "rate_limit_excluded_paths", ["/health"])
settings.rate_limit_excluded_prefixes = getattr(settings, "rate_limit_excluded_prefixes", ["/docs", "/openapi", "/redoc"])

# Auth vs unauth defaults (used when specific endpoints are not matched)
settings.rate_limit_unauth_default_limit = getattr(settings, "rate_limit_unauth_default_limit", 30)
settings.rate_limit_unauth_default_window_seconds = getattr(
    settings, "rate_limit_unauth_default_window_seconds", 3600
)

# Endpoint-specific rule mapping: keys are (METHOD, PATH)
# Values: {limit, window_seconds, endpoint_key}
settings.rate_limit_rules = {
    ("POST", "/notifications"): {
        "limit": 100,
        "window_seconds": 3600,
        "endpoint_key": "post_notifications",
    },
    ("GET", "/notifications"): {
        "limit": 500,
        "window_seconds": 3600,
        "endpoint_key": "get_notifications",
    },
    ("POST", "/auth/login"): {
        "limit": 10,
        "window_seconds": 60,
        "endpoint_key": "post_auth_login",
    },
    ("*", "*"): None,
}


# Redis client singleton used by middleware.
# Uses the same Redis URL already configured for Celery.
try:
    from redis.asyncio import Redis as AsyncRedis

    settings._rate_limit_redis = AsyncRedis.from_url(settings.redis_broker_url, decode_responses=False)
except Exception:
    settings._rate_limit_redis = None
