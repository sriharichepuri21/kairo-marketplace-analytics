from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Address


class AddressRepository:
    @staticmethod
    def list_for_user(
        database: Session,
        user_id: UUID,
    ) -> list[Address]:
        statement = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(
                Address.is_default.desc(),
                Address.created_at.asc(),
                Address.id.asc(),
            )
        )

        return list(database.scalars(statement).all())

    @staticmethod
    def get_for_user(
        database: Session,
        user_id: UUID,
        address_id: UUID,
    ) -> Address | None:
        statement = select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )

        return database.scalar(statement)

    @staticmethod
    def has_any(
        database: Session,
        user_id: UUID,
    ) -> bool:
        statement = select(Address.id).where(Address.user_id == user_id).limit(1)

        return database.scalar(statement) is not None

    @staticmethod
    def clear_defaults(
        database: Session,
        user_id: UUID,
        exclude_address_id: UUID | None = None,
    ) -> None:
        conditions = [
            Address.user_id == user_id,
            Address.is_default.is_(True),
        ]

        if exclude_address_id is not None:
            conditions.append(Address.id != exclude_address_id)

        statement = (
            update(Address)
            .where(*conditions)
            .values(
                is_default=False,
                updated_at=func.now(),
            )
            .execution_options(
                synchronize_session="fetch",
            )
        )

        database.execute(statement)

    @staticmethod
    def first_for_user(
        database: Session,
        user_id: UUID,
    ) -> Address | None:
        statement = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(
                Address.created_at.asc(),
                Address.id.asc(),
            )
            .limit(1)
        )

        return database.scalar(statement)

    @staticmethod
    def add(
        database: Session,
        address: Address,
    ) -> None:
        database.add(address)
        database.flush()

    @staticmethod
    def delete(
        database: Session,
        address: Address,
    ) -> None:
        database.delete(address)
        database.flush()
