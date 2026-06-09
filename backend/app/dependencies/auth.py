from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise AuthError()
        user_id = uuid.UUID(str(sub))
    except (JWTError, ValueError):
        raise AuthError()

    user = await session.get(User, user_id)
    if not user:
        raise AuthError()

    return user

