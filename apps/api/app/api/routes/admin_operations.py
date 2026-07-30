from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.core.database import get_db
from app.schemas.admin_operations import (
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


@router.get(
    "/summary",
    response_model=OperationsSummaryResponse,
    summary="Get marketplace operations summary",
)
def get_operations_summary(
    _admin_user: AdminUser,
    database: DatabaseSession,
) -> OperationsSummaryResponse:
    return OperationsService.get_summary(
        database
    )
