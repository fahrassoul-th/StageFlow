from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.permissions import require_program_manager
from app.models.user import User
from app.repositories.application_repository import (
    ApplicationRepository,
    get_application_repository,
)
from app.repositories.offer_repository import OfferRepository, get_offer_repository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", responses={403: {"description": "Only a program manager can view stats"}})
async def get_stats(
    current_user: Annotated[User, Depends(require_program_manager)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
) -> dict[str, dict[str, int]]:
    """Offer and application counts grouped by status (program manager only)."""
    return {
        "offers_by_status": await offers.count_by_status(),
        "applications_by_status": await applications.count_by_status(),
    }
