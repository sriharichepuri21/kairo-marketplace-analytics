from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CustomerEvent,
    Order,
    Product,
)


class CustomerEventRepository:
    @staticmethod
    def add(
        database: Session,
        event: CustomerEvent,
    ) -> None:
        database.add(event)

    @staticmethod
    def product_exists(
        database: Session,
        product_id: UUID,
    ) -> bool:
        product = database.scalar(
            select(Product.id).where(
                Product.id == product_id,
            )
        )

        return product is not None

    @staticmethod
    def order_belongs_to_user(
        database: Session,
        order_id: UUID,
        user_id: UUID,
    ) -> bool:
        order = database.scalar(
            select(Order.id).where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        )

        return order is not None

    @staticmethod
    def list_for_user(
        database: Session,
        user_id: UUID,
        *,
        limit: int,
    ) -> list[CustomerEvent]:
        statement = (
            select(CustomerEvent)
            .where(
                CustomerEvent.user_id == user_id,
            )
            .order_by(
                CustomerEvent.occurred_at.desc(),
                CustomerEvent.id.desc(),
            )
            .limit(limit)
        )

        return list(
            database.scalars(statement).all()
        )
