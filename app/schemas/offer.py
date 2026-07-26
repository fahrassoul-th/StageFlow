import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.offer import OfferStatus


class OfferCreateRequest(BaseModel):
    """What the client actually sends in the request body."""

    title: str | None = None
    mission: str | None = None
    skills: str | None = None


class OfferCreate(BaseModel):
    """What actually gets persisted - company_id is added server-side from
    the authenticated user, never taken from client input."""

    company_id: int
    title: str | None = None
    mission: str | None = None
    skills: str | None = None


class OfferUpdate(BaseModel):
    title: str | None = None
    mission: str | None = None
    skills: str | None = None
    status: OfferStatus | None = None
    updated_at: datetime.datetime | None = None


class OfferReviewRequest(BaseModel):
    decision: Literal["publish", "reject"]


class OfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    title: str | None
    mission: str | None
    skills: str | None
    status: OfferStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
