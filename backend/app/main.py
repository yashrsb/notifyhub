from app.api.v1.routes import api_router
from app.core.exceptions import register_exception_handlers
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="notifyhub", version="1.0.0")

    app.include_router(api_router, prefix="/api/v1")

    register_exception_handlers(app)

    # Phase 5 distributed rate limiting (middleware)
    from app.middleware.rate_limit_middleware import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)

    from app.db.session import get_engine
    from app.services.health_service import DependencyCheckResult, HealthService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "notifyhub",
            "version": "1.0.0",
        }

    @app.get("/ready")
    async def ready() -> dict:
        async def _check() -> DependencyCheckResult:
            sessionmaker = async_sessionmaker(
                get_engine(), expire_on_commit=False, class_=AsyncSession
            )
            async with sessionmaker() as session:
                checker = HealthService(session=session)
                return await checker.check_ready()

        result = await _check()
        if result.database and result.redis:
            return {
                "status": "ready",
                "database": "connected",
                "redis": "connected",
                "celery": result.celery,
            }

        from fastapi import status
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "connected" if result.database else "disconnected",
                "redis": "connected" if result.redis else "disconnected",
                "celery": result.celery,
            },
        )

    @app.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    return app


app = create_app()
