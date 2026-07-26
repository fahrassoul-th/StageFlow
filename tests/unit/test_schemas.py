import pytest
from pydantic import ValidationError

from app.models.role import RoleEnum
from app.schemas.auth import UserRegister
from app.schemas.offer import OfferReviewRequest
from app.schemas.users import UserRead


def test_user_register_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(
            username="bob",
            email="not-an-email",
            password="longenoughpw",
            full_name="Bob",
            role=RoleEnum.student,
        )


def test_user_register_rejects_short_password():
    with pytest.raises(ValidationError):
        UserRegister(
            username="bob",
            email="bob@x.com",
            password="short",
            full_name="Bob",
            role=RoleEnum.student,
        )


def test_user_register_rejects_short_username():
    with pytest.raises(ValidationError):
        UserRegister(
            username="ab",
            email="bob@x.com",
            password="longenoughpw",
            full_name="Bob",
            role=RoleEnum.student,
        )


def test_offer_review_request_rejects_unknown_decision():
    with pytest.raises(ValidationError):
        OfferReviewRequest(decision="delete")


def test_user_read_schema_never_exposes_hashed_password():
    assert "hashed_password" not in UserRead.model_fields
