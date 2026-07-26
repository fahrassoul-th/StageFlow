import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.role import RoleEnum


class UserUpdate(BaseModel):
    """Only used as BaseRepository's generic UpdateSchemaType - no route
    exposes profile editing for this subject."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    hashed_password: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime.datetime
