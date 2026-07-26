import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    """Assembled server-side (offer_id from the path, student_id from the
    token) - never bound directly to a client request body."""

    offer_id: int
    student_id: int


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    updated_at: datetime.datetime | None = None


class ApplicationDecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    offer_id: int
    student_id: int
    status: ApplicationStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
