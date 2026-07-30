"""Mirrors the course's own example (seance 6, section 1.5.2 "Mocks et
patches"): patch a repository method to simulate a database failure and
confirm it surfaces as a 500 instead of being silently swallowed or
returning a misleadingly successful response."""

from unittest.mock import AsyncMock, patch

from app.models.role import RoleEnum
from app.repositories.offer_repository import OfferRepository


async def test_offer_catalog_surfaces_repository_failure_as_500(
    client, register_and_login
):
    _, student = await register_and_login("student", RoleEnum.student)

    with patch.object(
        OfferRepository,
        "list_published",
        new_callable=AsyncMock,
        side_effect=Exception("DB connection lost"),
    ):
        response = await client.get("/offers", headers=student)

    assert response.status_code == 500
