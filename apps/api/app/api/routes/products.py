from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import (
    CategoryResponse,
    ProductDetailResponse,
    ProductPageResponse,
)
from app.services import ProductService


router = APIRouter(
    prefix="/api/v1",
    tags=["Catalogue"],
)


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List product categories",
)
def list_categories(
    database: Session = Depends(get_db),
) -> list[CategoryResponse]:
    return ProductService.list_categories(database)


@router.get(
    "/products",
    response_model=ProductPageResponse,
    summary="Search and filter products",
)
def list_products(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
    category: str | None = Query(
        default=None,
        description="Category slug, such as laptops.",
    ),
    brand: str | None = Query(
        default=None,
        max_length=120,
    ),
    min_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),
    max_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),
    in_stock: bool | None = Query(default=None),
    sort: Literal[
        "newest",
        "price_asc",
        "price_desc",
        "rating_desc",
        "name_asc",
    ] = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    database: Session = Depends(get_db),
) -> ProductPageResponse:
    return ProductService.list_products(
        database,
        search=search,
        category_slug=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product details",
)
def get_product(
    product_id: UUID,
    database: Session = Depends(get_db),
) -> ProductDetailResponse:
    return ProductService.get_product(
        database,
        product_id,
    )
