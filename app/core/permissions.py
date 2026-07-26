from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.core.errors import PermissionDeniedError
from app.core.security import get_current_user
from app.models.role import RoleEnum
from app.models.user import User


def require_roles(*roles: RoleEnum) -> Callable[[User], User]:
    """Build a FastAPI dependency that only lets the given roles through.

    Centralizing this here means routes never branch on `current_user.role`
    themselves - they just declare which roles are allowed. Doesn't need to
    be async itself: it only inspects the User object get_current_user (an
    async dependency) already resolved.
    """

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedError(
                f"Role '{current_user.role.value}' is not allowed to perform this action"
            )
        return current_user

    return dependency


require_student = require_roles(RoleEnum.student)
require_company = require_roles(RoleEnum.company)
require_program_manager = require_roles(RoleEnum.program_manager)
require_admin = require_roles(RoleEnum.admin)
