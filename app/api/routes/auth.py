from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.core.errors import BusinessRuleError, NotAuthenticatedError
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.repositories.user_repository import UserRepository, get_user_repository
from app.schemas.auth import Token, TokenRefresh, UserCreate, UserRegister
from app.schemas.users import UserRead
from app.utils.hashing import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Email or username is already taken"}},
)
async def register(
    payload: UserRegister,
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    """Create an account with any role (student, company, program_manager, admin)."""
    if await users.get_by_email(payload.email) is not None:
        raise BusinessRuleError("Email is already registered")
    if await users.get_by_username(payload.username) is not None:
        raise BusinessRuleError("Username is already taken")

    user = await users.create(
        UserCreate(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
        )
    )
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    responses={401: {"description": "Incorrect username/password, or account inactive"}},
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> Token:
    """OAuth2 password flow: exchange username + password for an access + refresh token."""
    user = await users.get_by_username(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise NotAuthenticatedError("Incorrect username or password")
    if not user.is_active:
        raise NotAuthenticatedError("User is inactive")

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"description": "Invalid, expired or non-refresh token"}},
)
async def refresh(
    payload: TokenRefresh,
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> Token:
    """Exchange a refresh token for a new access + refresh token pair."""
    token_payload = decode_token(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise NotAuthenticatedError("Invalid token type")

    subject = token_payload.get("sub")
    if subject is None:
        raise NotAuthenticatedError("Invalid token payload")

    user = await users.get(int(subject))
    if user is None or not user.is_active:
        raise NotAuthenticatedError("User not found or inactive")

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
