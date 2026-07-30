from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.core.database import get_db
from app.schemas.admin_operations import (
    OperationsOrderStatusResponse,
    OperationsRevenueTrendResponse,
    OperationsSummaryResponse,
)
from app.services.operations_service import (
    OperationsService,
)

router = APIRouter(
    prefix="/api/v1/admin/operations",
    tags=["Admin Operations"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

AnalysisDays = Annotated[
    int,
    Query(
        ge=1,
        le=3650,
    ),
]


@router.get(
    "/summary",
    response_model=OperationsSummaryResponse,
    summary="Get marketplace operations summary",
)
def get_operations_summary(
    _admin_user: AdminUser,
    database: DatabaseSession,
    days: AnalysisDays = 90,
) -> OperationsSummaryResponse:
    return OperationsService.get_summary(
        database,
        days=days,
    )


@router.get(
    "/revenue-trend",
    response_model=OperationsRevenueTrendResponse,
    summary="Get marketplace revenue trend",
)
def get_operations_revenue_trend(
    _admin_user: AdminUser,
    database: DatabaseSession,
    days: AnalysisDays = 90,
) -> OperationsRevenueTrendResponse:
    return OperationsService.get_revenue_trend(
        database,
        days=days,
    )


@router.get(
    "/order-statuses",
    response_model=OperationsOrderStatusResponse,
    summary="Get marketplace order statuses",
)
def get_operations_order_statuses(
    _admin_user: AdminUser,
    database: DatabaseSession,
    days: AnalysisDays = 90,
) -> OperationsOrderStatusResponse:
    return OperationsService.get_order_statuses(
        database,
        days=days,
    )
