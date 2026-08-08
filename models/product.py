from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(
        min_length=1,
        max_length=100,
        index=True
    )

    description: Optional[str] = None

    price: float = Field(gt=0)

    stock: int = Field(ge=0)

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class ProductCreate(SQLModel):
    name: str = Field(
        min_length=1,
        max_length=100
    )

    description: Optional[str] = None

    price: float = Field(gt=0)

    stock: int = Field(ge=0)


class ProductUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    description: Optional[str] = None

    price: Optional[float] = Field(
        default=None,
        gt=0
    )

    stock: Optional[int] = Field(
        default=None,
        ge=0
    )


class ProductRead(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    created_at: datetime
    updated_at: datetime