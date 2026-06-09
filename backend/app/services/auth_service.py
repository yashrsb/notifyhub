from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.users import User


async def register_user(*, session: AsyncSession, email: str, password: str) -> User:
    existing = await session.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if user:
        raise ConflictError(message="Email already registered")

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def login_user(*, session: AsyncSession, email: str, password: str) -> str:
    existing = await session.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError(message="Invalid credentials")

    token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=60))
    return token

