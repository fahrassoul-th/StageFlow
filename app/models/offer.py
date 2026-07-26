import datetime
import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class OfferStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    published = "published"
    rejected = "rejected"


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Nullable on purpose: a company may create a bare draft and complete it
    # later. The "must be filled in" rule only applies at publish time.
    title: Mapped[str | None] = mapped_column(String(255))
    mission: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)

    status: Mapped[OfferStatus] = mapped_column(default=OfferStatus.draft)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    company: Mapped["User"] = relationship(back_populates="offers")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )
