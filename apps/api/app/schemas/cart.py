from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1, le=10_000)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=10_000)


class CartProductResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    brand: str
    image_url: str | None


class CartItemResponse(BaseModel):
    id: UUID
    product: CartProductResponse
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    available_quantity: int


class CartResponse(BaseModel):
    id: UUID
    user_id: UUID
    items: list[CartItemResponse]
    total_quantity: int
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime
