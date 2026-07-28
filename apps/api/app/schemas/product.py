from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategorySummary


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_url: str
    alt_text: str | None
    display_order: int


class InventoryResponse(BaseModel):
    available_quantity: int
    reserved_quantity: int
    in_stock: bool


class ProductListItem(BaseModel):
    id: UUID
    name: str
    slug: str
    brand: str
    price: Decimal
    discount_price: Decimal | None
    effective_price: Decimal
    average_rating: Decimal
    image_url: str | None
    available_quantity: int
    in_stock: bool
    category: CategorySummary


class ProductDetailResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    brand: str
    price: Decimal
    discount_price: Decimal | None
    effective_price: Decimal
    average_rating: Decimal
    is_active: bool
    category: CategorySummary
    images: list[ProductImageResponse]
    inventory: InventoryResponse


class ProductPageResponse(BaseModel):
    items: list[ProductListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
