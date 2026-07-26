from typing import Any, Generic, Optional, Sequence, Type, TypeVar, cast

from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD repository shared by every domain repository."""

    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: int) -> Optional[ModelType]:
        result = await self.db.execute(
            select(self.model).where(getattr(self.model, "id") == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, data: CreateSchemaType) -> ModelType:
        obj = self.model(**data.model_dump())
        self.db.add(obj)
        await self.db.flush()  # get the id without committing
        await self.db.refresh(obj)
        return obj

    async def update(self, id: int, data: UpdateSchemaType) -> Optional[ModelType]:
        update_data = data.model_dump(exclude_none=True)
        if not update_data:
            return await self.get(id)

        await self.db.execute(
            update(self.model).where(getattr(self.model, "id") == id).values(**update_data)
        )
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        result = await self.db.execute(delete(self.model).where(getattr(self.model, "id") == id))
        return cast(Any, result).rowcount > 0
