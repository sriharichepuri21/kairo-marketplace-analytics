from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

DataQualityRunStatus = Literal[
    "running",
    "passed",
    "warning",
    "failed",
]

DataQualityCheckStatus = Literal[
    "passed",
    "warning",
    "failed",
]

DataQualitySeverity = Literal[
    "info",
    "warning",
    "error",
]


class DataQualityCheckResponse(BaseModel):
    id: UUID
    check_name: str
    check_category: str
    check_source: str
    target_name: str | None

    status: DataQualityCheckStatus
    severity: DataQualitySeverity

    observed_value: Any
    expected_value: Any
    failure_count: int = Field(ge=0)

    message: str | None
    details: dict[str, Any]

    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class DataQualityRunSummaryResponse(BaseModel):
    id: UUID
    run_type: str
    status: DataQualityRunStatus
    triggered_by: str

    total_checks: int = Field(ge=0)
    passed_checks: int = Field(ge=0)
    warning_checks: int = Field(ge=0)
    failed_checks: int = Field(ge=0)

    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class DataQualityRunDetailResponse(DataQualityRunSummaryResponse):
    metadata: dict[str, Any]
    checks: list[DataQualityCheckResponse]


class DataQualityRunPageResponse(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    items: list[DataQualityRunSummaryResponse]
