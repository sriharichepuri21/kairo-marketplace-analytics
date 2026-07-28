from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import check_database_connection


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and database health",
)
def health_check(response: Response) -> HealthResponse:
    try:
        check_database_connection()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return HealthResponse(
            status="unhealthy",
            service="available",
            database="unavailable",
        )

    return HealthResponse(
        status="healthy",
        service="available",
        database="available",
    )
