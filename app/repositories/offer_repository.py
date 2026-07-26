from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.offer import Offer, OfferStatus
from app.repositories.base import BaseRepository
from app.schemas.offer import OfferCreate, OfferUpdate


class OfferRepository(BaseRepository[Offer, OfferCreate, OfferUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Offer, db)

    async def list_published(self, *, skip: int = 0, limit: int = 20) -> list[Offer]:
        result = await self.db.execute(
            select(Offer)
            .where(Offer.status == OfferStatus.published)
            .order_by(Offer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_company(
        self, company_id: int, *, skip: int = 0, limit: int = 20
    ) -> list[Offer]:
        result = await self.db.execute(
            select(Offer)
            .where(Offer.company_id == company_id)
            .order_by(Offer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Offer.status, func.count(Offer.id)).group_by(Offer.status)
        )
        return {status.value: count for status, count in result.all()}


def get_offer_repository(db: AsyncSession = Depends(get_db)) -> OfferRepository:
    return OfferRepository(db)
