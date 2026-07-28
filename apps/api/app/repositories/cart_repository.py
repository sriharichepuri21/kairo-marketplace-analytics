from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Cart, CartItem, Product


class CartRepository:
    @staticmethod
    def get_by_user_id(
        database: Session,
        user_id: UUID,
    ) -> Cart | None:
        statement = (
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.product)
                .selectinload(Product.images),
                selectinload(Cart.items)
                .selectinload(CartItem.product)
                .selectinload(Product.inventory),
            )
            .where(Cart.user_id == user_id)
            .execution_options(populate_existing=True)
        )

        return database.scalar(statement)

    @classmethod
    def get_or_create(
        cls,
        database: Session,
        user_id: UUID,
    ) -> Cart:
        existing_cart = cls.get_by_user_id(database, user_id)

        if existing_cart is not None:
            return existing_cart

        database.add(Cart(user_id=user_id))

        try:
            database.commit()
        except IntegrityError:
            database.rollback()

        cart = cls.get_by_user_id(database, user_id)

        if cart is None:
            raise RuntimeError("Unable to create customer cart.")

        return cart

    @staticmethod
    def get_active_product(
        database: Session,
        product_id: UUID,
    ) -> Product | None:
        statement = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.inventory),
            )
            .where(
                Product.id == product_id,
                Product.is_active.is_(True),
            )
        )

        return database.scalar(statement)

    @classmethod
    def save_cart(
        cls,
        database: Session,
        cart: Cart,
    ) -> Cart:
        database.commit()
        database.expire_all()

        refreshed_cart = cls.get_by_user_id(
            database,
            cart.user_id,
        )

        if refreshed_cart is None:
            raise RuntimeError("Unable to reload customer cart.")

        return refreshed_cart

    @staticmethod
    def commit(database: Session) -> None:
        database.commit()
