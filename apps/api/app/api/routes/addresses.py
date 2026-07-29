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
    AddressCreate,
    AddressResponse,
    AddressUpdate,
)
from app.services import AddressService

router = APIRouter(
    prefix="/api/v1/addresses",
    tags=["Addresses"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "",
    response_model=list[AddressResponse],
    summary="List the customer's addresses",
)
def list_addresses(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> list[AddressResponse]:
    return AddressService.list_addresses(
        database,
        current_user,
    )


@router.post(
    "",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shipping address",
)
def create_address(
    address_data: AddressCreate,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AddressResponse:
    return AddressService.create_address(
        database,
        current_user,
        address_data,
    )


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Get a shipping address",
)
def get_address(
    address_id: UUID,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AddressResponse:
    return AddressService.get_address(
        database,
        current_user,
        address_id,
    )


@router.patch(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Update a shipping address",
)
def update_address(
    address_id: UUID,
    address_data: AddressUpdate,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AddressResponse:
    return AddressService.update_address(
        database,
        current_user,
        address_id,
        address_data,
    )


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shipping address",
)
def delete_address(
    address_id: UUID,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    AddressService.delete_address(
        database,
        current_user,
        address_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
