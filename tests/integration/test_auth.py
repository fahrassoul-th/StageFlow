from jose import jwt

from app.core.config import get_settings
from app.models.role import RoleEnum


async def test_register_and_login_flow(client):
    response = await client.post(
        "/auth/register",
        json={
            "username": "ada",
            "email": "a@b.com",
            "password": "secret123",
            "full_name": "A",
            "role": "student",
        },
    )
    assert response.status_code == 201
    assert "hashed_password" not in response.json()

    response = await client.post(
        "/auth/register",
        json={
            "username": "ada2",
            "email": "a@b.com",
            "password": "secret123",
            "full_name": "A",
            "role": "student",
        },
    )
    assert response.status_code == 400

    response = await client.post(
        "/auth/register",
        json={
            "username": "ada",
            "email": "other@b.com",
            "password": "secret123",
            "full_name": "A",
            "role": "student",
        },
    )
    assert response.status_code == 400

    response = await client.post(
        "/auth/login", data={"username": "ada", "password": "wrong-password"}
    )
    assert response.status_code == 401

    response = await client.post("/auth/login", data={"username": "ada", "password": "secret123"})
    assert response.status_code == 200
    tokens = response.json()
    assert "refresh_token" in tokens

    response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "ada"


async def test_users_me_requires_authentication(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_refresh_token_flow(client, register_and_login):
    user, headers = await register_and_login("ada", RoleEnum.student)

    response = await client.post("/auth/login", data={"username": "ada", "password": "secret123"})
    refresh_token = response.json()["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_tokens = response.json()

    response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert response.status_code == 200

    # using an access token where a refresh token is expected must fail
    response = await client.post(
        "/auth/refresh", json={"refresh_token": new_tokens["access_token"]}
    )
    assert response.status_code == 401


async def test_refresh_rejects_token_without_subject(client):
    settings = get_settings()
    token = jwt.encode({"type": "refresh"}, settings.secret_key, algorithm=settings.algorithm)
    response = await client.post("/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


async def test_refresh_rejects_unknown_user(client):
    settings = get_settings()
    token = jwt.encode(
        {"sub": "999999", "type": "refresh"}, settings.secret_key, algorithm=settings.algorithm
    )
    response = await client.post("/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


async def test_login_rejects_inactive_user(client, db_session):
    from app.repositories.user_repository import UserRepository

    response = await client.post(
        "/auth/register",
        json={
            "username": "inactive",
            "email": "inactive@x.com",
            "password": "secret123",
            "full_name": "Inactive",
            "role": "student",
        },
    )
    assert response.status_code == 201

    # No admin endpoint exists to deactivate an account (out of scope for
    # this subject's minimal endpoint list), so we flip the flag directly
    # through the repository to exercise the login-side check.
    users = UserRepository(db_session)
    user = await users.get_by_username("inactive")
    user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/auth/login", data={"username": "inactive", "password": "secret123"}
    )
    assert response.status_code == 401
