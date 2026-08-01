from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AdminUser
from app.core.database import get_db
from app.schemas.admin_data_quality import (
    DataQualityRunDetailResponse,
    DataQualityRunPageResponse,
)
from app.services.data_quality_service import (
    DataQualityService,
)

router = APIRouter(
    prefix="/api/v1/admin/data-quality",
    tags=["Admin Data Quality"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "/latest",
    response_model=DataQualityRunDetailResponse,
    summary="Get the latest data-quality run",
)
def get_latest_data_quality_run(
    _admin_user: AdminUser,
    database: DatabaseSession,
) -> DataQualityRunDetailResponse:
    return DataQualityService.get_latest_run(database)


@router.get(
    "/runs",
    response_model=DataQualityRunPageResponse,
    summary="List data-quality runs",
)
def list_data_quality_runs(
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
) -> DataQualityRunPageResponse:
    return DataQualityService.list_runs(
        database,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/runs/{run_id}",
    response_model=DataQualityRunDetailResponse,
    summary="Get one data-quality run",
)
def get_data_quality_run(
    run_id: UUID,
    _admin_user: AdminUser,
    database: DatabaseSession,
) -> DataQualityRunDetailResponse:
    return DataQualityService.get_run(
        database,
        run_id,
    )
