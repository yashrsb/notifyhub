from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response
from app.db.session import get_db
from app.services.auth_service import login_user, register_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.core.exceptions import ConflictError

router = APIRouter()


@router.post("/register")
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_db)):
    user = await register_user(session=session, email=req.email, password=req.password)
    return {"success": True, "data": {"id": str(user.id), "email": user.email}}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_db)):
    token = await login_user(session=session, email=req.email, password=req.password)
    return TokenResponse(access_token=token)

