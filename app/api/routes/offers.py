from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.permissions import require_company, require_program_manager
from app.core.security import get_current_user
from app.models.offer import Offer, OfferStatus
from app.models.role import RoleEnum
from app.models.user import User
from app.repositories.offer_repository import OfferRepository, get_offer_repository
from app.schemas.offer import (
    OfferCreate,
    OfferCreateRequest,
    OfferRead,
    OfferReviewRequest,
    OfferUpdate,
)
from app.utils.pagination import PageParams, pagination_params
from app.utils.time import utcnow

router = APIRouter(prefix="/offers", tags=["offers"])


def _visible_or_404(offer: Offer | None, current_user: User) -> Offer:
    """Applies the "404 = absent or not visible" rule: existence of an offer
    that isn't yours (as a company) or isn't published (as a student) is
    never revealed via a 403."""
    if offer is None:
        raise NotFoundError("Offer not found")
    if current_user.role == RoleEnum.student and offer.status != OfferStatus.published:
        raise NotFoundError("Offer not found")
    if current_user.role == RoleEnum.company and offer.company_id != current_user.id:
        raise NotFoundError("Offer not found")
    return offer


@router.post(
    "",
    response_model=OfferRead,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"description": "Only a company account can create an offer"}},
)
async def create_offer(
    payload: OfferCreateRequest,
    current_user: Annotated[User, Depends(require_company)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
) -> OfferRead:
    """Create a draft offer (company only). Fields may be left empty for now;
    they must be filled in before the offer can be published."""
    data = OfferCreate(company_id=current_user.id, **payload.model_dump())
    offer = await offers.create(data)
    return OfferRead.model_validate(offer)


@router.get("", response_model=list[OfferRead])
async def list_offers(
    current_user: Annotated[User, Depends(get_current_user)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
    page: Annotated[PageParams, Depends(pagination_params)],
) -> list[OfferRead]:
    """Role-aware catalog: a company sees its own pipeline (any status), a
    program manager/admin sees every offer (needed to find submitted ones
    to review), everyone else only sees the published catalog."""
    if current_user.role == RoleEnum.company:
        results = await offers.list_by_company(
            current_user.id, skip=page.skip, limit=page.limit
        )
    elif current_user.role in (RoleEnum.program_manager, RoleEnum.admin):
        results = await offers.get_all(skip=page.skip, limit=page.limit)
    else:
        results = await offers.list_published(skip=page.skip, limit=page.limit)
    return [OfferRead.model_validate(o) for o in results]


@router.get(
    "/{offer_id}",
    response_model=OfferRead,
    responses={404: {"description": "Offer absent, or not visible to this account"}},
)
async def get_offer(
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
) -> OfferRead:
    """Fetch a single offer. Returns 404 (never 403) if it exists but isn't
    visible to the caller, so a competitor's draft is never confirmed to exist."""
    offer = _visible_or_404(await offers.get(offer_id), current_user)
    return OfferRead.model_validate(offer)


@router.patch(
    "/{offer_id}/submit",
    response_model=OfferRead,
    responses={
        400: {"description": "Offer is not in draft status"},
        404: {"description": "Offer absent, or not owned by this company"},
    },
)
async def submit_offer(
    offer_id: int,
    current_user: Annotated[User, Depends(require_company)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
) -> OfferRead:
    """Transition an offer draft -> submitted (owning company only)."""
    offer = await offers.get(offer_id)
    if offer is None or offer.company_id != current_user.id:
        raise NotFoundError("Offer not found")
    if offer.status != OfferStatus.draft:
        raise BusinessRuleError("Only a draft offer can be submitted")

    updated = await offers.update(
        offer_id, OfferUpdate(status=OfferStatus.submitted, updated_at=utcnow())
    )
    return OfferRead.model_validate(updated)


@router.patch(
    "/{offer_id}/review",
    response_model=OfferRead,
    responses={
        400: {
            "description": "Offer is not submitted, or publishing an "
            "incomplete offer (missing title/mission/skills)"
        },
        403: {"description": "Only a program manager can review an offer"},
        404: {"description": "Offer not found"},
    },
)
async def review_offer(
    offer_id: int,
    payload: OfferReviewRequest,
    current_user: Annotated[User, Depends(require_program_manager)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
) -> OfferRead:
    """Publish or reject a submitted offer (program manager only). Publishing
    requires title, mission and skills to be filled in; rejecting doesn't."""
    offer = await offers.get(offer_id)
    if offer is None:
        raise NotFoundError("Offer not found")
    if offer.status != OfferStatus.submitted:
        raise BusinessRuleError("Only a submitted offer can be reviewed")

    if payload.decision == "publish":
        if not (offer.title and offer.mission and offer.skills):
            raise BusinessRuleError(
                "Title, mission and skills must be filled in before publishing"
            )
        new_status = OfferStatus.published
    else:
        new_status = OfferStatus.rejected

    updated = await offers.update(
        offer_id, OfferUpdate(status=new_status, updated_at=utcnow())
    )
    return OfferRead.model_validate(updated)
