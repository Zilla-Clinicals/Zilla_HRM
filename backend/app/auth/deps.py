import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import can
from app.auth.tokens import decode_access_token
from app.db import get_session
from app.models._base import Role
from app.models.users import User

security = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired token"
        ) from exc

    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "User not found or inactive"
        )
    return user


def require_role(*roles: Role):
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return user

    return _check


def require_cap(capability: str):
    """Dependency that allows the request only if the user's role has the capability."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not can(user.role, capability):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return user

    return _check
