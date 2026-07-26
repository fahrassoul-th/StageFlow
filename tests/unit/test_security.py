import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.errors import NotAuthenticatedError
from app.core.security import create_access_token, create_refresh_token, decode_token, get_current_user
from app.models.role import RoleEnum
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate
from app.utils.hashing import hash_password, verify_password


def test_hash_password_round_trip():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip():
    token = create_access_token(1, extra_data={"username": "ada"})
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["type"] == "access"
    assert payload["username"] == "ada"


def test_refresh_token_round_trip():
    token = create_refresh_token(1)
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"


def test_decode_invalid_token_raises_401():
    with pytest.raises(NotAuthenticatedError):
        decode_token("not-a-real-jwt")


def test_decode_token_missing_subject_is_allowed_but_unusable():
    """decode_token itself only validates the signature; callers are
    responsible for checking "sub" is present (get_current_user does)."""
    settings = get_settings()
    token = jwt.encode({}, settings.secret_key, algorithm=settings.algorithm)
    payload = decode_token(token)
    assert payload.get("sub") is None


async def test_get_current_user_rejects_token_without_subject(db_session):
    settings = get_settings()
    token = jwt.encode({"type": "access"}, settings.secret_key, algorithm=settings.algorithm)
    with pytest.raises(NotAuthenticatedError):
        await get_current_user(token=token, db=db_session)


async def test_get_current_user_rejects_non_int_subject(db_session):
    token = create_access_token("not-an-int")
    with pytest.raises(NotAuthenticatedError):
        await get_current_user(token=token, db=db_session)


async def test_get_current_user_rejects_unknown_user(db_session):
    token = create_access_token(999999)
    with pytest.raises(NotAuthenticatedError):
        await get_current_user(token=token, db=db_session)


async def test_get_current_user_rejects_refresh_token(db_session):
    token = create_refresh_token(1)
    with pytest.raises(NotAuthenticatedError):
        await get_current_user(token=token, db=db_session)


async def test_get_current_user_rejects_inactive_user(db_session):
    users = UserRepository(db_session)
    user = await users.create(
        UserCreate(
            username="inactive",
            email="inactive@x.com",
            hashed_password=hash_password("pw"),
            full_name="Inactive",
            role=RoleEnum.student,
            is_active=False,
        )
    )
    await db_session.commit()

    token = create_access_token(user.id)
    with pytest.raises(NotAuthenticatedError):
        await get_current_user(token=token, db=db_session)
