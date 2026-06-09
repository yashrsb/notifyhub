from app.api.v1.routes import api_router
from app.core.exceptions import register_exception_handlers
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="notifyhub", version="1.0.0")

    app.include_router(api_router, prefix="/api/v1")

    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

