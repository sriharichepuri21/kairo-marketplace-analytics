from decimal import Decimal
from typing import Annotated, Literal
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

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

SearchQuery = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=200,
    ),
]

CategoryQuery = Annotated[
    str | None,
    Query(
        description="Category slug, such as laptops.",
    ),
]

BrandQuery = Annotated[
    str | None,
    Query(max_length=120),
]

MinimumPriceQuery = Annotated[
    Decimal | None,
    Query(ge=0),
]

MaximumPriceQuery = Annotated[
    Decimal | None,
    Query(ge=0),
]

StockQuery = Annotated[
    bool | None,
    Query(),
]

ProductSort = Literal[
    "newest",
    "price_asc",
    "price_desc",
    "rating_desc",
    "name_asc",
]

SortQuery = Annotated[
    ProductSort,
    Query(),
]

PageQuery = Annotated[
    int,
    Query(ge=1),
]

PageSizeQuery = Annotated[
    int,
    Query(ge=1, le=100),
]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List product categories",
)
def list_categories(
    database: DatabaseSession,
) -> list[CategoryResponse]:
    return ProductService.list_categories(database)


@router.get(
    "/products",
    response_model=ProductPageResponse,
    summary="Search and filter products",
)
def list_products(
    database: DatabaseSession,
    search: SearchQuery = None,
    category: CategoryQuery = None,
    brand: BrandQuery = None,
    min_price: MinimumPriceQuery = None,
    max_price: MaximumPriceQuery = None,
    in_stock: StockQuery = None,
    sort: SortQuery = "newest",
    page: PageQuery = 1,
    page_size: PageSizeQuery = 24,
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
    database: DatabaseSession,
) -> ProductDetailResponse:
    return ProductService.get_product(
        database,
        product_id,
    )
