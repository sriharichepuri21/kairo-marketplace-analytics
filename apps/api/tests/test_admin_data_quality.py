from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    DataQualityCheckResult,
    DataQualityRun,
    User,
)

client = TestClient(app)

BASE_PATH = "/api/v1/admin/data-quality"


class AuthenticatedUser(TypedDict):
    user_id: UUID
    email: str
    headers: dict[str, str]


class DataQualityContext(TypedDict):
    admin: AuthenticatedUser
    customer: AuthenticatedUser
    older_run_id: UUID
    latest_run_id: UUID


def create_authenticated_user(
    role: str,
) -> AuthenticatedUser:
    email = f"data-quality-{role}-{uuid4()}@example.com"

    password = "StrongDataQualityPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": (f"Data Quality {role.title()}"),
            "password": password,
        },
    )

    assert register_response.status_code == 201

    database = SessionLocal()

    try:
        user = database.scalar(select(User).where(User.email == email))

        assert user is not None

        user.role = role
        database.commit()

        user_id = user.id

    finally:
        database.close()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "user_id": user_id,
        "email": email,
        "headers": {
            "Authorization": (f"Bearer {token}"),
        },
    }


def create_quality_run(
    database: Session,
    *,
    started_at: datetime,
    triggered_by: str,
    check_statuses: list[str],
) -> DataQualityRun:
    passed_checks = check_statuses.count("passed")

    warning_checks = check_statuses.count("warning")

    failed_checks = check_statuses.count("failed")

    if failed_checks:
        run_status = "failed"
    elif warning_checks:
        run_status = "warning"
    else:
        run_status = "passed"

    finished_at = started_at + timedelta(seconds=1)

    run = DataQualityRun(
        run_type="operational",
        status=run_status,
        triggered_by=triggered_by,
        started_at=started_at,
        finished_at=finished_at,
        total_checks=len(check_statuses),
        passed_checks=passed_checks,
        warning_checks=warning_checks,
        failed_checks=failed_checks,
        run_metadata={
            "test_run": True,
            "runner_version": "pytest",
        },
    )

    database.add(run)
    database.flush()

    severity_by_status = {
        "passed": "info",
        "warning": "warning",
        "failed": "error",
    }

    category_by_status = {
        "passed": "freshness",
        "warning": "reconciliation",
        "failed": "relationships",
    }

    for index, check_status in enumerate(
        check_statuses,
        start=1,
    ):
        failure_count = 0 if check_status == "passed" else 1

        database.add(
            DataQualityCheckResult(
                run_id=run.id,
                check_name=(f"pytest_{check_status}_{index}"),
                check_category=(category_by_status[check_status]),
                check_source="pytest",
                target_name="pytest_dataset",
                status=check_status,
                severity=(severity_by_status[check_status]),
                observed_value=failure_count,
                expected_value=0,
                failure_count=failure_count,
                message=(f"Pytest {check_status} result."),
                details={
                    "test_result": True,
                },
                started_at=started_at,
                finished_at=finished_at,
            )
        )

    database.flush()

    return run


def delete_test_records(
    run_ids: list[UUID],
    emails: list[str],
) -> None:
    database = SessionLocal()

    try:
        if run_ids:
            database.execute(delete(DataQualityRun).where(DataQualityRun.id.in_(run_ids)))

        users = database.scalars(select(User).where(User.email.in_(emails))).all()

        for user in users:
            database.delete(user)

        database.commit()

    finally:
        database.close()


@pytest.fixture(scope="module")
def data_quality_context() -> Generator[
    DataQualityContext,
    None,
    None,
]:
    admin = create_authenticated_user("admin")

    customer = create_authenticated_user("customer")

    database = SessionLocal()

    run_ids: list[UUID] = []

    try:
        base_time = datetime.now(UTC) + timedelta(hours=1)

        older_run = create_quality_run(
            database,
            started_at=base_time,
            triggered_by="pytest-older",
            check_statuses=[
                "passed",
            ],
        )

        latest_run = create_quality_run(
            database,
            started_at=(base_time + timedelta(minutes=1)),
            triggered_by="pytest-latest",
            check_statuses=[
                "passed",
                "warning",
                "failed",
            ],
        )

        database.commit()

        run_ids = [
            older_run.id,
            latest_run.id,
        ]

    finally:
        database.close()

    try:
        yield {
            "admin": admin,
            "customer": customer,
            "older_run_id": run_ids[0],
            "latest_run_id": run_ids[1],
        }

    finally:
        delete_test_records(
            run_ids,
            [
                admin["email"],
                customer["email"],
            ],
        )


def test_data_quality_endpoints_require_authentication(
    data_quality_context: DataQualityContext,
) -> None:
    paths = [
        f"{BASE_PATH}/latest",
        f"{BASE_PATH}/runs",
        (f"{BASE_PATH}/runs/{data_quality_context['latest_run_id']}"),
    ]

    for path in paths:
        response = client.get(path)

        assert response.status_code == 401


def test_customer_cannot_access_data_quality_api(
    data_quality_context: DataQualityContext,
) -> None:
    paths = [
        f"{BASE_PATH}/latest",
        f"{BASE_PATH}/runs",
        (f"{BASE_PATH}/runs/{data_quality_context['latest_run_id']}"),
    ]

    for path in paths:
        response = client.get(
            path,
            headers=(data_quality_context["customer"]["headers"]),
        )

        assert response.status_code == 403


def test_admin_can_get_latest_data_quality_run(
    data_quality_context: DataQualityContext,
) -> None:
    response = client.get(
        f"{BASE_PATH}/latest",
        headers=(data_quality_context["admin"]["headers"]),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["id"] == str(data_quality_context["latest_run_id"])

    assert payload["status"] == "failed"
    assert payload["triggered_by"] == ("pytest-latest")

    assert payload["total_checks"] == 3
    assert payload["passed_checks"] == 1
    assert payload["warning_checks"] == 1
    assert payload["failed_checks"] == 1

    assert (
        payload["passed_checks"] + payload["warning_checks"] + payload["failed_checks"]
        == payload["total_checks"]
    )

    assert len(payload["checks"]) == 3

    assert [check["status"] for check in payload["checks"]] == [
        "failed",
        "warning",
        "passed",
    ]

    assert payload["metadata"]["test_run"] is True


def test_admin_can_list_runs_with_pagination(
    data_quality_context: DataQualityContext,
) -> None:
    first_response = client.get(
        (f"{BASE_PATH}/runs?page=1&page_size=1"),
        headers=(data_quality_context["admin"]["headers"]),
    )

    assert first_response.status_code == 200

    first_payload = first_response.json()

    assert first_payload["page"] == 1
    assert first_payload["page_size"] == 1
    assert first_payload["total_items"] >= 2
    assert len(first_payload["items"]) == 1

    assert first_payload["items"][0]["id"] == str(data_quality_context["latest_run_id"])

    assert "checks" not in first_payload["items"][0]

    assert (
        first_payload["total_pages"]
        == (first_payload["total_items"] + first_payload["page_size"] - 1)
        // first_payload["page_size"]
    )

    second_response = client.get(
        (f"{BASE_PATH}/runs?page=2&page_size=1"),
        headers=(data_quality_context["admin"]["headers"]),
    )

    assert second_response.status_code == 200

    second_payload = second_response.json()

    assert len(second_payload["items"]) == 1

    assert second_payload["items"][0]["id"] == str(data_quality_context["older_run_id"])


def test_admin_can_get_one_data_quality_run(
    data_quality_context: DataQualityContext,
) -> None:
    run_id = data_quality_context["older_run_id"]

    response = client.get(
        f"{BASE_PATH}/runs/{run_id}",
        headers=(data_quality_context["admin"]["headers"]),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["id"] == str(run_id)
    assert payload["status"] == "passed"
    assert payload["triggered_by"] == ("pytest-older")

    assert payload["total_checks"] == 1
    assert payload["passed_checks"] == 1
    assert payload["warning_checks"] == 0
    assert payload["failed_checks"] == 0

    assert len(payload["checks"]) == 1
    assert payload["checks"][0]["status"] == "passed"


def test_unknown_data_quality_run_returns_404(
    data_quality_context: DataQualityContext,
) -> None:
    response = client.get(
        f"{BASE_PATH}/runs/{uuid4()}",
        headers=(data_quality_context["admin"]["headers"]),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == ("Data-quality run was not found.")


def test_run_history_pagination_validation(
    data_quality_context: DataQualityContext,
) -> None:
    invalid_queries = [
        "page=0",
        "page_size=0",
        "page_size=101",
    ]

    for query in invalid_queries:
        response = client.get(
            f"{BASE_PATH}/runs?{query}",
            headers=(data_quality_context["admin"]["headers"]),
        )

        assert response.status_code == 422
