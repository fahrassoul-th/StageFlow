import datetime
import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.offer import Offer
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    status: Mapped[ApplicationStatus] = mapped_column(default=ApplicationStatus.pending)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    offer: Mapped["Offer"] = relationship(back_populates="applications")
    student: Mapped["User"] = relationship(back_populates="applications")
