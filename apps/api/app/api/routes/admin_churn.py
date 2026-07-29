from typing import (
    Annotated,
    Literal,
)
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.core.database import get_db
from app.schemas import (
    CustomerChurnScorePage,
    CustomerChurnScoreResponse,
    CustomerChurnSummaryResponse,
)
from app.services import CustomerChurnService

router = APIRouter(
    prefix="/api/v1/admin/churn",
    tags=["Admin Churn"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

RiskSegment = Literal[
    "high_risk",
    "medium_risk",
    "low_risk",
]


@router.get(
    "/summary",
    response_model=CustomerChurnSummaryResponse,
    summary="Get the latest churn-risk summary",
)
def get_churn_summary(
    _admin_user: AdminUser,
    database: DatabaseSession,
) -> CustomerChurnSummaryResponse:
    return CustomerChurnService.get_summary(
        database
    )


@router.get(
    "/customers",
    response_model=CustomerChurnScorePage,
    summary="List customer churn scores",
)
def list_churn_customers(
    _admin_user: AdminUser,
    database: DatabaseSession,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
    risk_segment: Annotated[
        RiskSegment | None,
        Query(),
    ] = None,
    predicted_churn: Annotated[
        bool | None,
        Query(),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=320,
        ),
    ] = None,
) -> CustomerChurnScorePage:
    return CustomerChurnService.list_customers(
        database,
        page=page,
        page_size=page_size,
        risk_segment=risk_segment,
        predicted_churn=predicted_churn,
        search=search,
    )


@router.get(
    "/customers/{user_id}",
    response_model=CustomerChurnScoreResponse,
    summary="Get one customer's churn score",
)
def get_churn_customer(
    user_id: UUID,
    _admin_user: AdminUser,
    database: DatabaseSession,
) -> CustomerChurnScoreResponse:
    return CustomerChurnService.get_customer(
        database,
        user_id,
    )
