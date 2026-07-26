from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.errors import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.permissions import require_program_manager, require_student
from app.core.security import get_current_user
from app.models.application import ApplicationStatus
from app.models.offer import OfferStatus
from app.models.role import RoleEnum
from app.models.user import User
from app.repositories.application_repository import (
    ApplicationRepository,
    get_application_repository,
)
from app.repositories.offer_repository import OfferRepository, get_offer_repository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDecisionRequest,
    ApplicationRead,
    ApplicationUpdate,
)
from app.utils.pagination import PageParams, pagination_params
from app.utils.time import utcnow

router = APIRouter(tags=["applications"])


@router.post(
    "/offers/{offer_id}/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "An active application already exists for this offer"},
        403: {"description": "Only a student can apply"},
        404: {"description": "Offer absent, or not published"},
    },
)
async def create_application(
    offer_id: int,
    current_user: Annotated[User, Depends(require_student)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
) -> ApplicationRead:
    """Apply to a published offer (student only). Rejects a second active
    application to the same offer (400)."""
    offer = await offers.get(offer_id)
    if offer is None or offer.status != OfferStatus.published:
        raise NotFoundError("Offer not found")

    if await applications.has_active_application(offer_id=offer_id, student_id=current_user.id):
        raise BusinessRuleError("You already have an active application for this offer")

    application = await applications.create(
        ApplicationCreate(offer_id=offer_id, student_id=current_user.id)
    )
    return ApplicationRead.model_validate(application)


@router.get("/applications/me", response_model=list[ApplicationRead])
async def list_my_applications(
    current_user: Annotated[User, Depends(require_student)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
    page: Annotated[PageParams, Depends(pagination_params)],
) -> list[ApplicationRead]:
    """List the caller's own applications (student only), paginated."""
    results = await applications.list_by_student(
        current_user.id, skip=page.skip, limit=page.limit
    )
    return [ApplicationRead.model_validate(a) for a in results]


@router.get(
    "/offers/{offer_id}/applications",
    response_model=list[ApplicationRead],
    responses={
        403: {"description": "Students cannot list an offer's applications"},
        404: {"description": "Offer absent, or owned by another company"},
    },
)
async def list_offer_applications(
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    offers: Annotated[OfferRepository, Depends(get_offer_repository)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
    page: Annotated[PageParams, Depends(pagination_params)],
) -> list[ApplicationRead]:
    """List applications to one offer (owning company, program manager or
    admin). A company probing another company's offer id gets 404, never
    403 - competitor offers must never be confirmed to exist."""
    if current_user.role not in (RoleEnum.company, RoleEnum.program_manager, RoleEnum.admin):
        raise PermissionDeniedError("Not allowed to list applications for an offer")

    offer = await offers.get(offer_id)
    if offer is None:
        raise NotFoundError("Offer not found")

    if current_user.role == RoleEnum.company and offer.company_id != current_user.id:
        raise NotFoundError("Offer not found")

    results = await applications.list_by_offer(offer_id, skip=page.skip, limit=page.limit)
    return [ApplicationRead.model_validate(a) for a in results]


@router.patch(
    "/applications/{application_id}/decision",
    response_model=ApplicationRead,
    responses={
        400: {"description": "Application is not pending (already decided)"},
        403: {"description": "Only a program manager can decide an application"},
        404: {"description": "Application not found"},
    },
)
async def decide_application(
    application_id: int,
    payload: ApplicationDecisionRequest,
    current_user: Annotated[User, Depends(require_program_manager)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
) -> ApplicationRead:
    """Accept or reject a pending application (program manager only).
    An already-decided application cannot be decided again (400)."""
    application = await applications.get(application_id)
    if application is None:
        raise NotFoundError("Application not found")
    if application.status != ApplicationStatus.pending:
        raise BusinessRuleError("Only a pending application can be decided")

    new_status = (
        ApplicationStatus.accepted
        if payload.decision == "accepted"
        else ApplicationStatus.rejected
    )
    updated = await applications.update(
        application_id, ApplicationUpdate(status=new_status, updated_at=utcnow())
    )
    return ApplicationRead.model_validate(updated)


@router.delete(
    "/applications/{application_id}",
    response_model=ApplicationRead,
    responses={
        400: {"description": "An accepted application cannot be withdrawn"},
        404: {"description": "Application absent, or not owned by this student"},
    },
)
async def withdraw_application(
    application_id: int,
    current_user: Annotated[User, Depends(require_student)],
    applications: Annotated[ApplicationRepository, Depends(get_application_repository)],
) -> ApplicationRead:
    """Withdraw the caller's own application (student only): a soft
    transition to `withdrawn`, not a row deletion, so the record stays
    auditable. Blocked once the application has been accepted."""
    application = await applications.get(application_id)
    if application is None or application.student_id != current_user.id:
        raise NotFoundError("Application not found")
    if application.status == ApplicationStatus.accepted:
        raise BusinessRuleError("An accepted application cannot be withdrawn")

    updated = await applications.update(
        application_id,
        ApplicationUpdate(status=ApplicationStatus.withdrawn, updated_at=utcnow()),
    )
    return ApplicationRead.model_validate(updated)
