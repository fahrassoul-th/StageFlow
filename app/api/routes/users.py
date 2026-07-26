from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.users import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    responses={401: {"description": "Missing, invalid or expired bearer token"}},
)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Return the profile of the user identified by the bearer token."""
    return UserRead.model_validate(current_user)
