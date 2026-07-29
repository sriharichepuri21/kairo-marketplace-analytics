from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.database import get_db
from app.schemas import (
    CheckoutRequest,
    OrderResponse,
)
from app.services import OrderService

router = APIRouter(
    prefix="/api/v1",
    tags=["Orders"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order from the cart",
)
def checkout(
    checkout_data: CheckoutRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> OrderResponse:
    return OrderService.checkout(
        database,
        current_user,
        checkout_data,
    )


@router.get(
    "/orders",
    response_model=list[OrderResponse],
    summary="List the customer's orders",
)
def list_orders(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> list[OrderResponse]:
    return OrderService.list_orders(
        database,
        current_user,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get an order",
)
def get_order(
    order_id: UUID,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> OrderResponse:
    return OrderService.get_order(
        database,
        current_user,
        order_id,
    )
