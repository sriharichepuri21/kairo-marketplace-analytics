from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CustomerEvent, User
from app.repositories.customer_event_repository import (
    CustomerEventRepository,
)
from app.schemas import (
    CustomerEventCreate,
    CustomerEventResponse,
)


class CustomerEventService:
    @staticmethod
    def _to_response(
        event: CustomerEvent,
    ) -> CustomerEventResponse:
        return CustomerEventResponse.model_validate(
            event
        )

    @staticmethod
    def _commit(
        database: Session,
    ) -> None:
        try:
            database.commit()
        except IntegrityError:
            database.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The customer event could not be saved.",
            ) from None

    @classmethod
    def create_event(
        cls,
        database: Session,
        current_user: User | None,
        event_data: CustomerEventCreate,
    ) -> CustomerEventResponse:
        if (
            current_user is None
            and event_data.session_id is None
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Anonymous events require a session_id."
                ),
            )

        if event_data.product_id is not None:
            product_exists = (
                CustomerEventRepository.product_exists(
                    database,
                    event_data.product_id,
                )
            )

            if not product_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found.",
                )

        if event_data.order_id is not None:
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=(
                        "Authentication is required "
                        "for order events."
                    ),
                )

            owns_order = (
                CustomerEventRepository
                .order_belongs_to_user(
                    database,
                    event_data.order_id,
                    current_user.id,
                )
            )

            if not owns_order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found.",
                )

        event = CustomerEvent(
            user_id=(
                current_user.id
                if current_user is not None
                else None
            ),
            session_id=event_data.session_id,
            event_type=event_data.event_type,
            product_id=event_data.product_id,
            order_id=event_data.order_id,
            properties=event_data.properties,
        )

        CustomerEventRepository.add(
            database,
            event,
        )

        cls._commit(database)
        database.refresh(event)

        return cls._to_response(event)

    @classmethod
    def list_my_events(
        cls,
        database: Session,
        current_user: User,
        *,
        limit: int,
    ) -> list[CustomerEventResponse]:
        events = (
            CustomerEventRepository.list_for_user(
                database,
                current_user.id,
                limit=limit,
            )
        )

        return [
            cls._to_response(event)
            for event in events
        ]
