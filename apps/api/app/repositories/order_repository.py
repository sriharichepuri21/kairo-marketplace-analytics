from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Address,
    Cart,
    CartItem,
    Inventory,
    Order,
    Product,
)


class OrderRepository:
    @staticmethod
    def lock_address(
        database: Session,
        user_id: UUID,
        address_id: UUID,
    ) -> Address | None:
        statement = (
            select(Address)
            .where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
            .with_for_update()
        )

        return database.scalar(statement)

    @staticmethod
    def lock_cart(
        database: Session,
        user_id: UUID,
    ) -> Cart | None:
        statement = select(Cart).where(Cart.user_id == user_id).with_for_update()

        return database.scalar(statement)

    @staticmethod
    def lock_cart_items(
        database: Session,
        cart_id: UUID,
    ) -> list[CartItem]:
        statement = (
            select(CartItem)
            .where(CartItem.cart_id == cart_id)
            .order_by(
                CartItem.created_at.asc(),
                CartItem.id.asc(),
            )
            .with_for_update()
        )

        return list(database.scalars(statement).all())

    @staticmethod
    def lock_products(
        database: Session,
        product_ids: list[UUID],
    ) -> list[Product]:
        statement = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id.asc())
            .with_for_update()
        )

        return list(database.scalars(statement).all())

    @staticmethod
    def lock_inventory(
        database: Session,
        product_ids: list[UUID],
    ) -> list[Inventory]:
        statement = (
            select(Inventory)
            .where(Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id.asc())
            .with_for_update()
        )

        return list(database.scalars(statement).all())

    @staticmethod
    def get_for_user(
        database: Session,
        user_id: UUID,
        order_id: UUID,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
            )
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
            .execution_options(
                populate_existing=True,
            )
        )

        return database.scalar(statement)

    @staticmethod
    def list_for_user(
        database: Session,
        user_id: UUID,
    ) -> list[Order]:
        statement = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
            )
            .where(Order.user_id == user_id)
            .order_by(
                Order.created_at.desc(),
                Order.id.desc(),
            )
        )

        return list(database.scalars(statement).all())
