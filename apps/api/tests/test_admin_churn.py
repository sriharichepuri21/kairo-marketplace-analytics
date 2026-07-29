from collections.abc import Generator
from datetime import (
    UTC,
    date,
    datetime,
    timedelta,
)
from decimal import Decimal
from typing import TypedDict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    CustomerChurnScore,
    User,
)

client = TestClient(app)


class AuthenticatedUser(TypedDict):
    user_id: UUID
    email: str
    headers: dict[str, str]


class ChurnContext(TypedDict):
    admin: AuthenticatedUser
    customer: AuthenticatedUser
    scored_user_id: UUID


def create_authenticated_user(
    role: str,
) -> AuthenticatedUser:
    email = (
        f"churn-{role}-{uuid4()}"
        "@example.com"
    )

    password = "StrongChurnPassword123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": (
                f"Churn {role.title()}"
            ),
            "password": password,
        },
    )

    assert response.status_code == 201

    database = SessionLocal()

    try:
        user = database.scalar(
            select(User).where(
                User.email == email
            )
        )

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

    token = login_response.json()[
        "access_token"
    ]

    return {
        "user_id": user_id,
        "email": email,
        "headers": {
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    }


def delete_users(
    emails: list[str],
) -> None:
    database = SessionLocal()

    try:
        users = database.scalars(
            select(User).where(
                User.email.in_(emails)
            )
        ).all()

        for user in users:
            database.delete(user)

        database.commit()

    finally:
        database.close()


@pytest.fixture
def churn_context() -> Generator[
    ChurnContext,
    None,
    None,
]:
    admin = create_authenticated_user(
        "admin"
    )

    customer = create_authenticated_user(
        "customer"
    )

    scored_customer = (
        create_authenticated_user(
            "customer"
        )
    )

    database = SessionLocal()

    try:
        score = CustomerChurnScore(
            user_id=(
                scored_customer["user_id"]
            ),
            feature_snapshot_date=date(
                2026,
                7,
                29,
            ),
            days_since_last_order=15,
            total_orders=2,
            orders_last_30d=1,
            orders_last_90d=2,
            lifetime_spend=Decimal(
                "12500.00"
            ),
            average_order_value=Decimal(
                "6250.00"
            ),
            spend_last_90d=Decimal(
                "12500.00"
            ),
            account_age_days=180,
            is_single_order_customer=False,
            churn_probability=Decimal(
                "0.1200000000"
            ),
            predicted_churn_flag=False,
            risk_rank=1,
            risk_percentile=Decimal(
                "1.0000000000"
            ),
            risk_decile=1,
            risk_segment="low_risk",
            recommended_action=(
                "standard_monitoring"
            ),
            scoring_population_size=1,
            probability_threshold=Decimal(
                "0.3100000000"
            ),
            model_name=(
                "live_compatible_behavioral"
            ),
            model_version=(
                f"test_churn_{uuid4()}"
            ),
            scored_at_utc=(
                datetime.now(UTC)
                + timedelta(days=1)
            ),
        )

        database.add(score)
        database.commit()

    finally:
        database.close()

    try:
        yield {
            "admin": admin,
            "customer": customer,
            "scored_user_id": (
                scored_customer["user_id"]
            ),
        }

    finally:
        delete_users(
            [
                admin["email"],
                customer["email"],
                scored_customer["email"],
            ]
        )


def test_churn_summary_requires_authentication(
    churn_context: ChurnContext,
) -> None:
    response = client.get(
        "/api/v1/admin/churn/summary"
    )

    assert response.status_code == 401


def test_customer_cannot_access_churn_api(
    churn_context: ChurnContext,
) -> None:
    response = client.get(
        "/api/v1/admin/churn/summary",
        headers=(
            churn_context[
                "customer"
            ]["headers"]
        ),
    )

    assert response.status_code == 403


def test_admin_can_get_churn_summary(
    churn_context: ChurnContext,
) -> None:
    response = client.get(
        "/api/v1/admin/churn/summary",
        headers=(
            churn_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "eligible_customers"
    ] == 1

    assert payload[
        "low_risk_customers"
    ] == 1

    assert payload[
        "predicted_churners"
    ] == 0


def test_admin_can_list_churn_customers(
    churn_context: ChurnContext,
) -> None:
    response = client.get(
        (
            "/api/v1/admin/churn/customers"
            "?risk_segment=low_risk"
        ),
        headers=(
            churn_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total_items"] == 1
    assert len(payload["items"]) == 1

    assert (
        payload["items"][0]["user_id"]
        == str(
            churn_context[
                "scored_user_id"
            ]
        )
    )


def test_admin_can_get_customer_score(
    churn_context: ChurnContext,
) -> None:
    user_id = churn_context[
        "scored_user_id"
    ]

    response = client.get(
        (
            "/api/v1/admin/churn/"
            f"customers/{user_id}"
        ),
        headers=(
            churn_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["user_id"] == str(
        user_id
    )

    assert payload[
        "risk_segment"
    ] == "low_risk"

    assert payload[
        "churn_probability"
    ] == pytest.approx(
        0.12
    )
