from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    username: str = Field(
        unique=True,
        index=True,
        min_length=3,
        max_length=50
    )

    email: EmailStr = Field(
        unique=True,
        index=True
    )

    hashed_password: str

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    role: str = Field(default="user")

    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    last_login: Optional[datetime] = None


class UserCreate(SQLModel):
    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: EmailStr

    password: str = Field(
        min_length=8
    )

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    role: str = Field(default="user")


class UserResponse(SQLModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime