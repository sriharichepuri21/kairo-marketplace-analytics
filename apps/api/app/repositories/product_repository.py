from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Inventory, Product


class ProductRepository:
    @staticmethod
    def list_categories(
        database: Session,
    ) -> list[tuple[Category, int]]:
        statement = (
            select(
                Category,
                func.count(Product.id).label("product_count"),
            )
            .outerjoin(
                Product,
                (Product.category_id == Category.id) & Product.is_active.is_(True),
            )
            .group_by(Category.id)
            .order_by(Category.name.asc())
        )

        rows = database.execute(statement).all()

        return [(category, int(product_count)) for category, product_count in rows]

    @staticmethod
    def get_product_by_id(
        database: Session,
        product_id: UUID,
    ) -> Product | None:
        statement = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
                selectinload(Product.inventory),
            )
            .where(
                Product.id == product_id,
                Product.is_active.is_(True),
            )
        )

        return database.scalar(statement)

    @staticmethod
    def list_products(
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
    ) -> tuple[list[Product], int]:
        effective_price = func.coalesce(
            Product.discount_price,
            Product.price,
        )

        filters = [Product.is_active.is_(True)]

        if search:
            search_pattern = f"%{search.strip()}%"

            filters.append(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.brand.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )

        if category_slug:
            filters.append(Category.slug == category_slug)

        if brand:
            filters.append(Product.brand.ilike(brand.strip()))

        if min_price is not None:
            filters.append(effective_price >= min_price)

        if max_price is not None:
            filters.append(effective_price <= max_price)

        if in_stock is True:
            filters.append(Inventory.available_quantity > 0)
        elif in_stock is False:
            filters.append(
                or_(
                    Inventory.product_id.is_(None),
                    Inventory.available_quantity <= 0,
                )
            )

        count_statement = (
            select(func.count(Product.id))
            .select_from(Product)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(
                Inventory,
                Inventory.product_id == Product.id,
            )
            .where(*filters)
        )

        total_items = int(database.scalar(count_statement) or 0)

        statement: Select[tuple[Product]] = (
            select(Product)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(
                Inventory,
                Inventory.product_id == Product.id,
            )
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
                selectinload(Product.inventory),
            )
            .where(*filters)
        )

        sort_options = {
            "newest": Product.created_at.desc(),
            "price_asc": effective_price.asc(),
            "price_desc": effective_price.desc(),
            "rating_desc": Product.average_rating.desc(),
            "name_asc": Product.name.asc(),
        }

        statement = (
            statement.order_by(
                sort_options.get(sort, Product.created_at.desc()),
                Product.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        products = list(database.scalars(statement).all())

        return products, total_items
