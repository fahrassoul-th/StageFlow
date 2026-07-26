from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.application import Application, ApplicationStatus
from app.repositories.base import BaseRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate

ACTIVE_STATUSES = (ApplicationStatus.pending, ApplicationStatus.accepted)


class ApplicationRepository(BaseRepository[Application, ApplicationCreate, ApplicationUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Application, db)

    async def has_active_application(self, *, offer_id: int, student_id: int) -> bool:
        result = await self.db.execute(
            select(Application.id).where(
                Application.offer_id == offer_id,
                Application.student_id == student_id,
                Application.status.in_(ACTIVE_STATUSES),
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_by_student(
        self, student_id: int, *, skip: int = 0, limit: int = 20
    ) -> list[Application]:
        result = await self.db.execute(
            select(Application)
            .where(Application.student_id == student_id)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_offer(
        self, offer_id: int, *, skip: int = 0, limit: int = 20
    ) -> list[Application]:
        result = await self.db.execute(
            select(Application)
            .where(Application.offer_id == offer_id)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Application.status, func.count(Application.id)).group_by(Application.status)
        )
        return {status.value: count for status, count in result.all()}


def get_application_repository(db: AsyncSession = Depends(get_db)) -> ApplicationRepository:
    return ApplicationRepository(db)
