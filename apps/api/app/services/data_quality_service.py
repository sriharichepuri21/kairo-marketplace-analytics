from math import ceil
from uuid import UUID

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.models import (
    DataQualityCheckResult,
    DataQualityRun,
)
from app.repositories.data_quality_repository import (
    DataQualityRepository,
)
from app.schemas.admin_data_quality import (
    DataQualityCheckResponse,
    DataQualityRunDetailResponse,
    DataQualityRunPageResponse,
    DataQualityRunSummaryResponse,
)

CHECK_STATUS_PRIORITY = {
    "failed": 1,
    "warning": 2,
    "passed": 3,
}


def build_run_summary(
    run: DataQualityRun,
) -> DataQualityRunSummaryResponse:
    return DataQualityRunSummaryResponse(
        id=run.id,
        run_type=run.run_type,
        status=run.status,
        triggered_by=run.triggered_by,
        total_checks=run.total_checks,
        passed_checks=run.passed_checks,
        warning_checks=run.warning_checks,
        failed_checks=run.failed_checks,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


def build_check_response(
    check: DataQualityCheckResult,
) -> DataQualityCheckResponse:
    return DataQualityCheckResponse(
        id=check.id,
        check_name=check.check_name,
        check_category=check.check_category,
        check_source=check.check_source,
        target_name=check.target_name,
        status=check.status,
        severity=check.severity,
        observed_value=check.observed_value,
        expected_value=check.expected_value,
        failure_count=check.failure_count,
        message=check.message,
        details=check.details,
        started_at=check.started_at,
        finished_at=check.finished_at,
        created_at=check.created_at,
    )


def build_run_detail(
    run: DataQualityRun,
) -> DataQualityRunDetailResponse:
    sorted_checks = sorted(
        run.checks,
        key=lambda check: (
            CHECK_STATUS_PRIORITY.get(
                check.status,
                99,
            ),
            check.check_category,
            check.check_name,
        ),
    )

    return DataQualityRunDetailResponse(
        **build_run_summary(run).model_dump(),
        metadata=run.run_metadata,
        checks=[build_check_response(check) for check in sorted_checks],
    )


class DataQualityService:
    @staticmethod
    def get_latest_run(
        database: Session,
    ) -> DataQualityRunDetailResponse:
        run = DataQualityRepository.get_latest_run(database)

        if run is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail=("No data-quality runs are available."),
            )

        return build_run_detail(run)

    @staticmethod
    def get_run(
        database: Session,
        run_id: UUID,
    ) -> DataQualityRunDetailResponse:
        run = DataQualityRepository.get_run_by_id(
            database,
            run_id,
        )

        if run is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail=("Data-quality run was not found."),
            )

        return build_run_detail(run)

    @staticmethod
    def list_runs(
        database: Session,
        *,
        page: int,
        page_size: int,
    ) -> DataQualityRunPageResponse:
        (
            runs,
            total_items,
        ) = DataQualityRepository.list_runs(
            database,
            page=page,
            page_size=page_size,
        )

        return DataQualityRunPageResponse(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(ceil(total_items / page_size) if total_items else 0),
            items=[build_run_summary(run) for run in runs],
        )
