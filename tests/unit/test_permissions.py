import pytest

from app.core.errors import PermissionDeniedError
from app.core.permissions import require_roles
from app.models.role import RoleEnum
from app.models.user import User


def _user(role: RoleEnum) -> User:
    return User(username="x", email="x@x.com", hashed_password="hashed", full_name="X", role=role)


def test_require_roles_accepts_matching_role():
    dependency = require_roles(RoleEnum.student)
    user = _user(RoleEnum.student)
    assert dependency(current_user=user) is user


def test_require_roles_accepts_any_of_several_roles():
    dependency = require_roles(RoleEnum.program_manager, RoleEnum.admin)
    assert dependency(current_user=_user(RoleEnum.admin)) is not None


def test_require_roles_rejects_non_matching_role():
    dependency = require_roles(RoleEnum.company)
    with pytest.raises(PermissionDeniedError):
        dependency(current_user=_user(RoleEnum.student))


@pytest.mark.parametrize(
    ("role", "should_pass"),
    [
        (RoleEnum.student, False),
        (RoleEnum.company, True),
        (RoleEnum.program_manager, False),
        (RoleEnum.admin, False),
    ],
)
def test_require_company_only_accepts_company_across_all_roles(
    role: RoleEnum, should_pass: bool
) -> None:
    """Exercises require_roles against every role in one pass, rather than
    one hand-picked accept case and one hand-picked reject case - catches
    a mistake like an extra role slipping into the allow-list."""
    dependency = require_roles(RoleEnum.company)
    user = _user(role)

    if should_pass:
        assert dependency(current_user=user) is user
    else:
        with pytest.raises(PermissionDeniedError):
            dependency(current_user=user)
