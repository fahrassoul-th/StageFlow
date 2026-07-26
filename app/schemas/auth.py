from pydantic import BaseModel, EmailStr, Field

from app.models.role import RoleEnum


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleEnum


class UserCreate(BaseModel):
    """What actually gets persisted - password already hashed server-side."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    hashed_password: str
    full_name: str
    role: RoleEnum
    is_active: bool = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    refresh_token: str
