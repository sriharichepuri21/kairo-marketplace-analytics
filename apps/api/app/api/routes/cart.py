from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.database import get_db
from app.schemas import (
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
)
from app.services import CartService

router = APIRouter(
    prefix="/api/v1/cart",
    tags=["Cart"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "",
    response_model=CartResponse,
    summary="Get the authenticated customer's cart",
)
def get_cart(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CartResponse:
    return CartService.get_cart(
        database,
        current_user,
    )


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product to the cart",
)
def add_cart_item(
    item_data: CartItemCreate,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CartResponse:
    return CartService.add_item(
        database,
        current_user,
        item_data,
    )


@router.patch(
    "/items/{item_id}",
    response_model=CartResponse,
    summary="Update a cart item's quantity",
)
def update_cart_item(
    item_id: UUID,
    item_data: CartItemUpdate,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CartResponse:
    return CartService.update_item(
        database,
        current_user,
        item_id,
        item_data,
    )


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from the cart",
)
def remove_cart_item(
    item_id: UUID,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    CartService.remove_item(
        database,
        current_user,
        item_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the customer's cart",
)
def clear_cart(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    CartService.clear_cart(
        database,
        current_user,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
