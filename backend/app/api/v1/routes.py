from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_notifications import router as notifications_router
from app.api.v1.routes_templates import router as templates_router
from fastapi.routing import APIRouter

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

