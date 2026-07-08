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


settings = Settings()


