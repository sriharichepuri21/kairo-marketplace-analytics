from collections.abc import Generator
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    DataQualityCheckResult,
    DataQualityRun,
)
from app.scripts import run_data_quality_checks as quality_runner


@pytest.fixture
def created_quality_run_ids() -> Generator[
    list[UUID],
    None,
    None,
]:
    run_ids: list[UUID] = []

    yield run_ids

    if not run_ids:
        return

    database = SessionLocal()

    try:
        database.execute(delete(DataQualityRun).where(DataQualityRun.id.in_(run_ids)))
        database.commit()

    finally:
        database.close()


def create_test_run(
    database: Session,
    *,
    total_checks: int,
) -> DataQualityRun:
    run = DataQualityRun(
        run_type="operational",
        status="running",
        triggered_by="pytest",
        total_checks=total_checks,
        run_metadata={
            "test_run": True,
        },
    )

    database.add(run)
    database.commit()
    database.refresh(run)

    return run


@pytest.mark.parametrize(
    (
        "statuses",
        "expected_status",
        "expected_passed",
        "expected_warnings",
        "expected_failed",
    ),
    [
        (
            ["passed", "passed", "passed"],
            "passed",
            3,
            0,
            0,
        ),
        (
            ["passed", "warning", "passed"],
            "warning",
            2,
            1,
            0,
        ),
        (
            ["passed", "warning", "failed"],
            "failed",
            1,
            1,
            1,
        ),
    ],
)
def test_finalize_run_calculates_status_and_counts(
    created_quality_run_ids: list[UUID],
    statuses: list[quality_runner.CheckStatus],
    expected_status: str,
    expected_passed: int,
    expected_warnings: int,
    expected_failed: int,
) -> None:
    database = SessionLocal()

    try:
        run = create_test_run(
            database,
            total_checks=len(statuses),
        )
        created_quality_run_ids.append(run.id)

        finalized_run = quality_runner.finalize_run(
            database,
            run.id,
            statuses,
        )

        assert finalized_run.status == expected_status
        assert finalized_run.passed_checks == expected_passed
        assert finalized_run.warning_checks == expected_warnings
        assert finalized_run.failed_checks == expected_failed
        assert finalized_run.finished_at is not None

        assert (
            finalized_run.passed_checks + finalized_run.warning_checks + finalized_run.failed_checks
            == finalized_run.total_checks
        )

    finally:
        database.close()


@pytest.mark.parametrize(
    (
        "observed_value",
        "nonzero_status",
        "expected_status",
    ),
    [
        (
            0,
            "failed",
            "passed",
        ),
        (
            2,
            "warning",
            "warning",
        ),
        (
            3,
            "failed",
            "failed",
        ),
    ],
)
def test_count_check_persists_expected_result(
    created_quality_run_ids: list[UUID],
    observed_value: int,
    nonzero_status: str,
    expected_status: str,
) -> None:
    database = SessionLocal()

    try:
        run = create_test_run(
            database,
            total_checks=1,
        )
        created_quality_run_ids.append(run.id)

        check = quality_runner.CountCheck(
            name=(f"pytest_count_check_{expected_status}"),
            category="business_rule",
            target_name="pytest",
            sql=f"SELECT {observed_value}",
            nonzero_status=nonzero_status,
            success_message="Test check passed.",
            issue_message="Test check found an issue.",
        )

        status = quality_runner.run_count_check(
            database,
            run.id,
            check,
        )

        result = database.scalar(
            select(DataQualityCheckResult).where(
                DataQualityCheckResult.run_id == run.id,
                DataQualityCheckResult.check_name == check.name,
            )
        )

        assert status == expected_status
        assert result is not None
        assert result.status == expected_status
        assert result.observed_value == observed_value
        assert result.expected_value == 0
        assert result.failure_count == observed_value

        expected_severity = {
            "passed": "info",
            "warning": "warning",
            "failed": "error",
        }[expected_status]

        assert result.severity == expected_severity
        assert result.finished_at is not None

    finally:
        database.close()


def test_sql_error_is_persisted_as_failed_check(
    created_quality_run_ids: list[UUID],
) -> None:
    database = SessionLocal()

    try:
        run = create_test_run(
            database,
            total_checks=1,
        )
        created_quality_run_ids.append(run.id)

        check = quality_runner.CountCheck(
            name="pytest_invalid_sql",
            category="business_rule",
            target_name="pytest",
            sql=("SELECT missing_column FROM missing_quality_table"),
            nonzero_status="failed",
            success_message="Unexpected success.",
            issue_message="Expected failure.",
        )

        status = quality_runner.run_count_check(
            database,
            run.id,
            check,
        )

        result = database.scalar(
            select(DataQualityCheckResult).where(
                DataQualityCheckResult.run_id == run.id,
                DataQualityCheckResult.check_name == check.name,
            )
        )

        assert status == "failed"
        assert result is not None
        assert result.status == "failed"
        assert result.severity == "error"
        assert result.failure_count == 1
        assert result.observed_value is None
        assert result.details["error_type"]
        assert result.details["error"]

    finally:
        database.close()


@pytest.mark.parametrize(
    (
        "timestamp_sql",
        "expected_status",
    ),
    [
        (
            "SELECT CURRENT_TIMESTAMP",
            "passed",
        ),
        (
            ("SELECT CURRENT_TIMESTAMP - INTERVAL '30 hours'"),
            "warning",
        ),
        (
            ("SELECT CURRENT_TIMESTAMP - INTERVAL '72 hours'"),
            "failed",
        ),
    ],
)
def test_freshness_check_classifies_age(
    created_quality_run_ids: list[UUID],
    timestamp_sql: str,
    expected_status: str,
) -> None:
    database = SessionLocal()

    try:
        run = create_test_run(
            database,
            total_checks=1,
        )
        created_quality_run_ids.append(run.id)

        check_name = f"pytest_freshness_{expected_status}"

        status = quality_runner.run_freshness_check(
            database,
            run_id=run.id,
            check_name=check_name,
            target_name="pytest",
            timestamp_sql=timestamp_sql,
            warning_hours=24,
            failure_hours=48,
        )

        result = database.scalar(
            select(DataQualityCheckResult).where(
                DataQualityCheckResult.run_id == run.id,
                DataQualityCheckResult.check_name == check_name,
            )
        )

        assert status == expected_status
        assert result is not None
        assert result.status == expected_status
        assert result.observed_value["latest_timestamp"]
        assert result.observed_value["age_hours"] is not None

        expected_failure_count = 0 if expected_status == "passed" else 1

        assert result.failure_count == expected_failure_count

    finally:
        database.close()


def test_invalid_freshness_thresholds_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=("Freshness warning hours must be positive"),
    ):
        quality_runner.run_checks(
            triggered_by="pytest",
            warning_hours=0,
            failure_hours=48,
        )

    with pytest.raises(
        ValueError,
        match=("Freshness failure hours must be greater"),
    ):
        quality_runner.run_checks(
            triggered_by="pytest",
            warning_hours=48,
            failure_hours=48,
        )


def test_repeated_runs_create_separate_history(
    created_quality_run_ids: list[UUID],
) -> None:
    first_run = quality_runner.run_checks(
        triggered_by="pytest",
        warning_hours=1_000_000,
        failure_hours=2_000_000,
    )

    second_run = quality_runner.run_checks(
        triggered_by="pytest",
        warning_hours=1_000_000,
        failure_hours=2_000_000,
    )

    created_quality_run_ids.extend(
        [
            first_run.id,
            second_run.id,
        ]
    )

    assert first_run.id != second_run.id

    database = SessionLocal()

    try:
        for run in (
            first_run,
            second_run,
        ):
            stored_results = database.scalar(
                select(func.count(DataQualityCheckResult.id)).where(
                    DataQualityCheckResult.run_id == run.id
                )
            )

            assert stored_results == run.total_checks

            assert run.passed_checks + run.warning_checks + run.failed_checks == run.total_checks

        stored_runs = database.scalar(
            select(func.count(DataQualityRun.id)).where(
                DataQualityRun.id.in_(
                    [
                        first_run.id,
                        second_run.id,
                    ]
                )
            )
        )

        assert stored_runs == 2

    finally:
        database.close()
