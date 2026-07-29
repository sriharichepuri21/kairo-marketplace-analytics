from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    CurrentUser,
    OptionalCurrentUser,
)
from app.core.database import get_db
from app.schemas import (
    CustomerEventCreate,
    CustomerEventResponse,
)
from app.services import CustomerEventService


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Customer Events"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "",
    response_model=CustomerEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a customer behavior event",
)
def create_customer_event(
    event_data: CustomerEventCreate,
    current_user: OptionalCurrentUser,
    database: DatabaseSession,
) -> CustomerEventResponse:
    return CustomerEventService.create_event(
        database,
        current_user,
        event_data,
    )


@router.get(
    "/me",
    response_model=list[CustomerEventResponse],
    summary="List the current customer's events",
)
def list_my_customer_events(
    current_user: CurrentUser,
    database: DatabaseSession,
    limit: Annotated[
        int,
        Query(ge=1, le=500),
    ] = 100,
) -> list[CustomerEventResponse]:
    return CustomerEventService.list_my_events(
        database,
        current_user,
        limit=limit,
    )
