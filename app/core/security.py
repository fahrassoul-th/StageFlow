from datetime import timedelta
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotAuthenticatedError
from app.db.session import get_db
from app.models.user import User
from app.utils.time import utcnow

settings = get_settings()

# tokenUrl points at the login endpoint's exact path (the subject names it
# "POST /auth/login", not the fil rouge's "/auth/token").
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(
    subject: str | int,
    extra_data: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a short-lived access JWT."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = utcnow() + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": utcnow(),
        "type": "access",
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int) -> str:
    """Generate a long-lived refresh JWT (no extra claims on purpose)."""
    expire = utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises 401 if invalid or expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise NotAuthenticatedError("Invalid or expired token") from exc


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise NotAuthenticatedError("Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise NotAuthenticatedError("Invalid token payload")

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise NotAuthenticatedError("Invalid token payload") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError("User not found or inactive")
    return user
