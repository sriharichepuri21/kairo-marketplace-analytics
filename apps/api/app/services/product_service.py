from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Product
from app.repositories import ProductRepository
from app.schemas import (
    CategoryResponse,
    CategorySummary,
    InventoryResponse,
    ProductDetailResponse,
    ProductImageResponse,
    ProductListItem,
    ProductPageResponse,
)


class ProductService:
    @staticmethod
    def _effective_price(product: Product) -> Decimal:
        return product.discount_price or product.price

    @staticmethod
    def _available_quantity(product: Product) -> int:
        if product.inventory is None:
            return 0

        return product.inventory.available_quantity

    @staticmethod
    def _primary_image(product: Product) -> str | None:
        if not product.images:
            return None

        return product.images[0].image_url

    @classmethod
    def _to_list_item(
        cls,
        product: Product,
    ) -> ProductListItem:
        available_quantity = cls._available_quantity(product)

        return ProductListItem(
            id=product.id,
            name=product.name,
            slug=product.slug,
            brand=product.brand,
            price=product.price,
            discount_price=product.discount_price,
            effective_price=cls._effective_price(product),
            average_rating=product.average_rating,
            image_url=cls._primary_image(product),
            available_quantity=available_quantity,
            in_stock=available_quantity > 0,
            category=CategorySummary.model_validate(
                product.category
            ),
        )

    @classmethod
    def _to_detail(
        cls,
        product: Product,
    ) -> ProductDetailResponse:
        available_quantity = cls._available_quantity(product)
        reserved_quantity = (
            product.inventory.reserved_quantity
            if product.inventory is not None
            else 0
        )

        return ProductDetailResponse(
            id=product.id,
            name=product.name,
            slug=product.slug,
            description=product.description,
            brand=product.brand,
            price=product.price,
            discount_price=product.discount_price,
            effective_price=cls._effective_price(product),
            average_rating=product.average_rating,
            is_active=product.is_active,
            category=CategorySummary.model_validate(
                product.category
            ),
            images=[
                ProductImageResponse.model_validate(image)
                for image in product.images
            ],
            inventory=InventoryResponse(
                available_quantity=available_quantity,
                reserved_quantity=reserved_quantity,
                in_stock=available_quantity > 0,
            ),
        )

    @staticmethod
    def list_categories(
        database: Session,
    ) -> list[CategoryResponse]:
        rows = ProductRepository.list_categories(database)

        return [
            CategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                product_count=product_count,
            )
            for category, product_count in rows
        ]

    @classmethod
    def list_products(
        cls,
        database: Session,
        *,
        search: str | None,
        category_slug: str | None,
        brand: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> ProductPageResponse:
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="min_price cannot be greater than max_price.",
            )

        products, total_items = ProductRepository.list_products(
            database,
            search=search,
            category_slug=category_slug,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        total_pages = (
            ceil(total_items / page_size)
            if total_items > 0
            else 0
        )

        return ProductPageResponse(
            items=[
                cls._to_list_item(product)
                for product in products
            ],
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    @classmethod
    def get_product(
        cls,
        database: Session,
        product_id: UUID,
    ) -> ProductDetailResponse:
        product = ProductRepository.get_product_by_id(
            database,
            product_id,
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        return cls._to_detail(product)
